from django.shortcuts import redirect, render
from amadeus import Client, ResponseError

#Amadeus API
amadeus = Client(
    client_id='H0uaXJjZTm9ePSQIe5Q59XiCGvEdZsm2',
    client_secret='ex0r2L2ew3PNSjTv'
)

#Converts city to properly formatted Iata code, whether you type in city or airport code
def toIataCode(city):
    response = None
    try:
        response = amadeus.reference_data.locations.get(
            keyword= city,
            subType="AIRPORT,CITY"
        )
    except ResponseError as error:
        print(error)
    possibleCities = []

    for data in response.data: 
        #For the united states
        if "stateCode" in data["address"]:
            possibleCities.append({"city":data["address"]["cityName"], 
                "state":data["address"]["stateCode"], 
                "iataCode":data["iataCode"], 
                "name":data["name"], 
                "country":data["address"]["countryName"]})
        #For international, although international is very limited on this API
        else:
            possibleCities.append({"city":data["address"]["cityName"], 
                "iataCode":data["iataCode"], 
                "name":data["name"], 
                "country":data["address"]["countryName"]})  

    return possibleCities

#Returns the cheapeast available flights based on the numberOfResults Requested
def availableFlights(fromCity, toCity, numberPeople, date, numberOfResults):
    response = None
    try:
        response = amadeus.shopping.flight_offers_search.get(
            currencyCode = "USD",
            originLocationCode=fromCity,
            destinationLocationCode=toCity,
            departureDate=date, #YYYY-MM-DD
            adults=numberPeople)
    except ResponseError as error:
        print(error)
    #Returns a list the size of of the number of results or if there are less then the length 
    #List of dictionaries containing all of the flight info
    flights = [response.data[i] for i in range(min(len(response.data),numberOfResults))]
    return flights

#Formats the list of dictionaries into a organized manner with organized nesting
def parseFlights(flightData):
    listParsedFlights = []
    for data in flightData:
        organizedDict = {
            "totTime":data["itineraries"][0]["duration"][2:],
            "departureTimeIataCode":[],
            "arrivalTimeIataCode":[],
            "departureTime":[],
            "arrivalTime":[],
            "cheapestPrice":None,
            "averagePrice":None,
            "expensivePrice":None,
            "layovers": 0,
            "layoverLoc":[],
            "deal": None,
            "totPrice":data["price"]["total"],
            "cabin":data["travelerPricings"][0]["fareDetailsBySegment"][0]["cabin"]}
            #Might be layovers therefore need to take into account multiple segments 
        for i in range(len(data["itineraries"][0]["segments"])):
            organizedDict["departureTimeIataCode"].append(data["itineraries"][0]["segments"][i]["departure"]["iataCode"])
            organizedDict["arrivalTimeIataCode"].append(data["itineraries"][0]["segments"][i]["arrival"]["iataCode"])
            organizedDict["departureTime"].append(data["itineraries"][0]["segments"][i]["departure"]["at"][-8:-3])
            organizedDict["arrivalTime"].append(data["itineraries"][0]["segments"][i]["arrival"]["at"][-8:-3])
        listParsedFlights.append(organizedDict)
    return listParsedFlights

#This only works with flights that have a large amount of values/popular airports
#Get request to see the usual prices for the flight, range: low, med, high
def relativePriceAnalysis(originIataCode, destinationIataCode, departureDate, parsedFlightsData):
    response = ""
    newParsedData = []
    for flight in parsedFlightsData:
        cost = float(flight["totPrice"])
        deal = ""
        try:
            response = amadeus.analytics.itinerary_price_metrics.get(
                                                originIataCode=originIataCode,
                                                destinationIataCode=destinationIataCode,
                                                departureDate=departureDate,
                                                currencyCode="USD",
                                                oneWay="true")
        except ResponseError as error:
            print(error)
        #Checking 
        if len(flight["departureTimeIataCode"]) >= 1:
            flight["layovers"] = len(flight["departureTimeIataCode"]) - 1
            flight["layoverLoc"] = [i for i in flight["departureTimeIataCode"] for j in flight["arrivalTimeIataCode"] if i == j]
        #Sometimes there is no analytics data therefore we ignore if nothing was read.
        if len(response.data) > 0:
            priceMetrics = response.data[0]["priceMetrics"]
            cheap = float(priceMetrics[1]["amount"])
            average = float(priceMetrics[2]["amount"])
            expensive = float(priceMetrics[3]["amount"])
            if cost <= cheap:
                deal = "Very Good Price"
            elif cost > cheap and cost < average:
                deal = "Good Price"
            elif cost == average:
                deal = "Average Price"
            elif cost > average and cost < expensive:
                deal = "Bad Price"
            elif cost >= expensive:
                deal = "Very Bad Price"
            flight["cheapestPrice"] = cheap
            flight["averagePrice"] = average
            flight["expensivePrice"] = expensive
            flight["deal"] = deal
        else: 
            #No data on the flight
            deal = "No Relative Price Comparisons Avaliable"
            flight["deal"] = deal
        newParsedData.append(flight)
    return newParsedData

#Link url
def bestFlight(request): 
    return render(request, 'bestFlightApp/index.html')

#Drives the code and recieves the user input from the browser
def main(request): 
    #Pulling info from user
    fromCity = request.POST.get("departureCity")
    toCity = request.POST.get("destinationCity")
    date = request.POST.get("departureDate")
    numPassengers = request.POST.get("numPassengers")

    if fromCity is not None and toCity is not None and date is not None:
        iataCodeFromCity = toIataCode(fromCity)[0]["iataCode"]
        iataCodeToCity = toIataCode(toCity)[0]["iataCode"]
        flights = availableFlights(iataCodeFromCity,iataCodeToCity,numPassengers,date,5)
        parsedFlightsData = parseFlights(flights)
        parsedFlightsData = relativePriceAnalysis(iataCodeFromCity, iataCodeToCity, date, parsedFlightsData)
        #Have to convert the list of flights to a dictionary in order to be able to pass the values to html
        parsedFlightsDataDict = {"flight"+str(index): value for index, value in enumerate(parsedFlightsData)}
        return render(request, 'bestFlightApp/price.html',parsedFlightsDataDict)
    return render(request, 'bestFlightApp/price.html')