# Production Flask Server Configuration
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from werkzeug.serving import WSGIRequestHandler
import signal
import atexit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ProductionConfig:
    """Production configuration for GCP deployment"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # GCP Configuration
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', 'bravo-dev-465400')
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'brimages')
    
    # Server Configuration
    HOST = os.environ.get('HOST', '0.0.0.0')  # GCP requires 0.0.0.0
    PORT = int(os.environ.get('PORT', 8080))  # GCP uses PORT env var
    
    # Development vs Production
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'
    
    # Timeouts and limits
    REQUEST_TIMEOUT = 300  # 5 minutes for image generation
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

class DevelopmentConfig(ProductionConfig):
    """Development configuration"""
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5003

def create_app(config_name='production'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Select configuration
    if config_name == 'development' or os.environ.get('FLASK_ENV') == 'development':
        app.config.from_object(DevelopmentConfig)
        logger.info("Starting in DEVELOPMENT mode")
    else:
        app.config.from_object(ProductionConfig)
        logger.info("Starting in PRODUCTION mode")
    
    # Configure Flask
    app.config['MAX_CONTENT_LENGTH'] = app.config['MAX_CONTENT_LENGTH']
    
    # Enable CORS
    CORS(app, origins=['*'])  # Configure more restrictively in production
    
    # Initialize GCP services
    try:
        from services.gcp_services import initialize_gcp_services
        initialize_gcp_services(app)
        logger.info("GCP services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GCP services: {e}")
        # Don't fail startup - use fallback modes
    
    # Register routes
    from routes import register_routes
    register_routes(app)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for GCP load balancer"""
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'environment': app.config['ENV']
        })
    
    return app

def graceful_shutdown(signum, frame):
    """Handle graceful shutdown"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)
    
    # Determine environment
    env = 'development' if len(sys.argv) > 1 and sys.argv[1] == 'dev' else 'production'
    
    # Create app
    app = create_app(env)
    
    logger.info(f"Starting server on {app.config['HOST']}:{app.config['PORT']}")
    logger.info(f"Environment: {app.config['ENV']}")
    logger.info(f"Debug mode: {app.config['DEBUG']}")
    
    try:
        if app.config['DEBUG']:
            # Development server
            app.run(
                host=app.config['HOST'],
                port=app.config['PORT'],
                debug=True,
                use_reloader=False,  # Disable reloader to prevent port conflicts
                threaded=True
            )
        else:
            # Production server (for local testing - use gunicorn in GCP)
            from waitress import serve
            serve(
                app,
                host=app.config['HOST'],
                port=app.config['PORT'],
                threads=4,
                connection_limit=100,
                cleanup_interval=30
            )
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

# WSGI entry point for gunicorn
app = create_app('production')
