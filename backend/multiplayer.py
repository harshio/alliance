from fastapi import WebSocket
class WebSocketManager:
    def __init__(self):
        #mapping client_id to websocket makes it possible
        #for us to to choose between websockets to 
        #send information to
        self.connected_clients: dict[str, WebSocket] = {}
        self.activeSet: int = 0
        self.host_client: dict[str, WebSocket] = {}
        self.playersDone: int = 0

    #this function connects a client to the server
    #and adds them to the list
    async def player_connect(self, websocket: WebSocket, client_id: str, client_number=2, server_number=3) -> bool:
        #websocket is a representation of the client
        #it contains information like the IP address of
        #the client
        if client_number == server_number:
            await websocket.accept()
            self.connected_clients[client_id] = websocket
            return True
        else:
            print("CRY ABOUT IT BITCH WE'RE TESTING")
            return False
    
    async def host_connect(self, websocket: WebSocket, client_id: str) -> bool:
        await websocket.accept()
        self.host_client[client_id] = websocket
        return True

    #this function disconnects a client from the server
    async def disconnect(self, client_id: str):
        self.connected_clients.pop(client_id, None)

    #this function gets the server to send a message to the client specified
    #by client_id. the message dict will require keys of content, type, 
    #and to
    async def send_message_to(self, client_id: str, message: dict):
        if client_id in self.connected_clients:
            await self.connected_clients[client_id].send_json(message)
            #as counter-intuitive as it is, this is actually sending the message
            #TO self.connected_clients[client_id], not from it