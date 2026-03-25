from app import create_app, socketio

# Get the Flask app instance
app = create_app()

if __name__ == '__main__':
    print("\n=== Starting TasteBudz API Server ===")
    print("• HTTP Server: http://localhost:5000")
    print("• WebSocket Endpoint: ws://localhost:5000")
    print("• API Base URL: http://localhost:5000/api/v1")
    print("\nPress Ctrl+C to stop the server\n")
    
    socketio.run(
        app,
        debug=True,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True
    )