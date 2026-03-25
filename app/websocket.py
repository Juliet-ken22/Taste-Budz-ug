# test_websocket.py
import socketio
import time

# Create a Socket.IO client
sio = socketio.Client(logger=True, engineio_logger=True)

# Event handlers
@sio.event
def connect():
    print("[SocketIO] Connected to server")

@sio.event
def disconnect():
    print("[SocketIO] Disconnected from server")

@sio.on('order_update')
def on_order_update(data):
    print("[SocketIO] Received order update:", data)

@sio.on('new_order')
def on_new_order(data):
    print("[SocketIO] Received new order:", data)

@sio.on('reservation_update')
def on_reservation_update(data):
    print("[SocketIO] Received reservation update:", data)

@sio.on('notification')
def on_notification(data):
    print("[SocketIO] Received notification:", data)

def test_socketio():
    try:
        # Connect to your Flask-SocketIO server
        # Use http://localhost:5000 for local dev or wss://admins.tastebz.com for production
        sio.connect('http://localhost:5000', transports=['websocket'])

        # Send a test event
        sio.emit('test_event', {'message': 'Hello from test script'})

        # Keep the connection alive for 10 seconds to receive events
        print("[SocketIO] Listening for events for 10 seconds...")
        time.sleep(10)

    except Exception as e:
        print(f"[SocketIO] Error: {e}")

    finally:
        sio.disconnect()
        print("[SocketIO] Client disconnected")

if __name__ == "__main__":
    test_socketio()
