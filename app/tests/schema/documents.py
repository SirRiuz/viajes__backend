"""GraphQL documents copied from the frontend (viajes__front/src/schema)."""

TOKEN_AUTH = """
  mutation TokenAuth($username: String!, $password: String!) {
    tokenAuth(username: $username, password: $password) { token }
  }
"""

ME = "query { me { id username firstName lastName email } }"

DRIVER_FIELDS = "id createAt shortId dni licenseId fullName"
DRIVER_LIST = "query GetDriverList($page: Int) { getDriverList(page: $page) { count pages next results { %s } } }" % DRIVER_FIELDS
GET_ACTIVE_DRIVERS = "query { getActiveDrivers { %s dniFileUrl licensePdfFileUrl signatureUrl } }" % DRIVER_FIELDS
CREATE_DRIVER = """
  mutation CreateDriver($fullName: String!, $dni: String!, $licenseId: String!) {
    createDriver(fullName: $fullName, dni: $dni, licenseId: $licenseId) { driver { %s } }
  }
""" % DRIVER_FIELDS
UPDATE_DRIVER = """
  mutation UpdateDriver($id: ID!, $fullName: String!, $dni: String!, $licenseId: String!) {
    updateDriver(id: $id, fullName: $fullName, dni: $dni, licenseId: $licenseId) { driver { %s } }
  }
""" % DRIVER_FIELDS
DELETE_DRIVER = "mutation DeleteDriver($id: String!) { deleteDriver(id: $id) { ok } }"

ROUTE_LIST = "query GetRouteList($page: Int) { getRouteList(page: $page) { count pages next results { id shortId routeName } } }"
GET_ACTIVE_ROUTES = "query { getActiveRoutes { id shortId routeName } }"
CREATE_ROUTE = "mutation CreateRoute($routeName: String!) { createRoute(routeName: $routeName) { route { id shortId routeName } } }"
UPDATE_ROUTE = "mutation UpdateRoute($id: ID!, $routeName: String!) { updateRoute(id: $id, routeName: $routeName) { route { id shortId routeName } } }"
DELETE_ROUTE = "mutation DeleteRoute($id: String!) { deleteRoute(id: $id) { success } }"

GET_ACTIVE_VESSELS = "query { getActiveVessels { id name seatCount } }"
CREATE_VESSEL = "mutation CreateVessel($name: String!, $seatCount: Int!) { createVessel(name: $name, seatCount: $seatCount) { ok } }"
UPDATE_VESSEL = "mutation UpdateVessel($id: String!, $name: String!, $seatCount: Int!) { updateVessel(id: $id, name: $name, seatCount: $seatCount) { ok } }"
DELETE_VESSEL = "mutation DeleteVessel($id: String!) { deleteVessel(id: $id) { ok } }"

CREATE_TICKET = """
  mutation CreateTicket($clientEmail: String, $clientIdNumber: String!, $clientName: String!, $clientPhone: String!,
                        $paymentMethod: String!, $seatNumber: Int!, $ticketPrice: String!, $tripId: String!) {
    createTicket(clientEmail: $clientEmail, clientIdNumber: $clientIdNumber, clientName: $clientName,
                 clientPhone: $clientPhone, paymentMethod: $paymentMethod, seatNumber: $seatNumber,
                 ticketPrice: $ticketPrice, tripId: $tripId) { ok error }
  }
"""
UPDATE_TICKET = """
  mutation UpdateTicket($id: String!, $tripId: String, $clientName: String, $clientIdNumber: String, $clientEmail: String,
                        $clientPhone: String, $seatNumber: String!, $paymentMethod: String, $ticketPrice: String!) {
    updateTicket(id: $id, tripId: $tripId, clientName: $clientName, clientIdNumber: $clientIdNumber,
                 clientEmail: $clientEmail, clientPhone: $clientPhone, seatNumber: $seatNumber,
                 paymentMethod: $paymentMethod, ticketPrice: $ticketPrice) { ok }
  }
"""
DELETE_TICKET = "mutation DeleteTicket($id: String!) { deleteTicket(id: $id) { success } }"

TRIP_LIST = """
  query GetTripList($page: Int, $prefix: String, $order: String) {
    getTripList(page: $page, prefix: $prefix, order: $order) {
      count pages next
      results {
        id index createAt createAtTime shortId dispatcher
        passengers { id shortId clientName clientEmail clientPhone clientIdNumber seatNumber ticketPrice paymentMethod }
        route { id routeName }
        vessel { id name seatCount }
        driver { id fullName dni licenseId signatureUrl }
      }
    }
  }
"""
CREATE_TRIP = """
  mutation CreateTrip($driverId: String!, $routeId: String!, $vesselId: String!, $dispatcher: String!) {
    createTrip(driverId: $driverId, routeId: $routeId, vesselId: $vesselId, dispatcher: $dispatcher) { ok }
  }
"""
UPDATE_TRIP = """
  mutation UpdateTrip($id: String!, $driverId: String!, $routeId: String!, $vesselId: String!, $dispatcher: String!) {
    updateTrip(id: $id, driverId: $driverId, routeId: $routeId, vesselId: $vesselId, dispatcher: $dispatcher) { ok }
  }
"""
DELETE_TRIP = "mutation DeleteTrip($id: String!) { deleteTrip(id: $id) { success } }"
GET_FREE_SEATS = "query GetFreeSeats($id: String!) { getTripById(id: $id) { freeSeats } }"
GET_TRIP_BY_ID = """
  query GetTripById($id: String!) {
    getTripById(id: $id) {
      id createAt dispatcher
      driver { id fullName licenseId }
      route { id routeName }
      vessel { id name seatCount }
      passengersCounter freeSeats
      passengers { id index createAt createAtTime shortId clientName clientEmail clientPhone clientIdNumber seatNumber ticketPrice paymentMethod }
    }
  }
"""
