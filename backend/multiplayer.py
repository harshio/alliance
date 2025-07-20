from fastapi import WebSocket
class WebSocketManager:
    def __init__(self):
        #mapping client_id to websocket makes it possible
        #for us to to choose between websockets to 
        #send information to
        self.connected_clients: dict[str, WebSocket] = {}

    #this function connects a client to the server
    #and adds them to the list
    async def connect(self, websocket: WebSocket, client_id: str):
        #websocket is a representation of the client
        #it contains information like the IP address of
        #the client
        await websocket.accept()
        self.connected_clients[client_id] = websocket

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