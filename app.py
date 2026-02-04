"""
Webshell Instance Spawner API for CTFd
Validates CTFd tokens and manages Docker containers for teams
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import requests
from docker_manager import DockerManager

# Configuration
CTFD_URL = os.environ.get('CTFD_URL', 'https://2k26-rsuctf.nulbytez.live')
WEBSHELL_BASE_URL = os.environ.get('WEBSHELL_BASE_URL', 'https://webshell.nullbytez.live')
CONTAINER_NETWORK = os.environ.get('CONTAINER_NETWORK', 'webshell-network')
CONTAINER_IMAGE = os.environ.get('CONTAINER_IMAGE', 'webshell-instance:latest')
CONTAINER_MEMORY_LIMIT = os.environ.get('CONTAINER_MEMORY_LIMIT', '512m')
CONTAINER_CPU_LIMIT = float(os.environ.get('CONTAINER_CPU_LIMIT', '0.5'))
CONTAINER_TIMEOUT_HOURS = int(os.environ.get('CONTAINER_TIMEOUT_HOURS', '24'))
API_SECRET = os.environ.get('API_SECRET', 'change-me-in-production')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=['*'])  # Configure appropriately for production

# Initialize Docker manager
docker_mgr = DockerManager(
    network_name=CONTAINER_NETWORK,
    image_name=CONTAINER_IMAGE,
    memory_limit=CONTAINER_MEMORY_LIMIT,
    cpu_limit=CONTAINER_CPU_LIMIT,
    timeout_hours=CONTAINER_TIMEOUT_HOURS,
    webshell_base_url=WEBSHELL_BASE_URL
)


def validate_ctfd_token(token):
    """
    Validate a CTFd token by calling the CTFd API
    Returns user and team information if valid
    """
    try:
        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }
        
        # Get current user info
        user_response = requests.get(
            f'{CTFD_URL}/api/v1/users/me',
            headers=headers,
            timeout=10
        )
        
        if user_response.status_code != 200:
            logger.warning(f"Token validation failed: {user_response.status_code}")
            return None
        
        user_data = user_response.json()
        
        if not user_data.get('success'):
            return None
        
        user = user_data.get('data', {})
        user_id = user.get('id')
        username = user.get('name', 'user')
        team_id = user.get('team_id')
        
        # If user has a team, get team info
        team_name = None
        if team_id:
            team_response = requests.get(
                f'{CTFD_URL}/api/v1/teams/{team_id}',
                headers=headers,
                timeout=10
            )
            
            if team_response.status_code == 200:
                team_data = team_response.json()
                if team_data.get('success'):
                    team_name = team_data.get('data', {}).get('name')
        
        # If no team, use username as team name (for individual mode)
        if not team_name:
            team_name = username
            team_id = f'user_{user_id}'
        
        return {
            'user_id': user_id,
            'username': username,
            'team_id': team_id,
            'team_name': team_name
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error validating token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        return None


def sanitize_team_name(team_name):
    """
    Sanitize team name for use in container naming
    """
    import re
    # Convert to lowercase, replace spaces and special chars with hyphens
    sanitized = re.sub(r'[^a-z0-9-]', '-', team_name.lower())
    # Remove consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    # Limit length
    return sanitized[:50] if sanitized else 'team'


# ============== API Endpoints ==============

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'webshell-api'
    })


@app.route('/api/validate-token', methods=['POST'])
def api_validate_token():
    """
    Validate a CTFd token and return user/team information
    """
    try:
        data = request.get_json()
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token is required'
            }), 400
        
        result = validate_ctfd_token(token)
        
        if result:
            return jsonify({
                'success': True,
                'user_id': result['user_id'],
                'username': result['username'],
                'team_id': result['team_id'],
                'team_name': result['team_name']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token'
            }), 401
            
    except Exception as e:
        logger.error(f"Error in validate-token: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/status', methods=['POST'])
def api_status():
    """
    Check the status of a team's webshell container
    """
    try:
        data = request.get_json()
        team_name = data.get('team_name', '').strip()
        
        if not team_name:
            return jsonify({
                'success': False,
                'error': 'Team name is required'
            }), 400
        
        sanitized_name = sanitize_team_name(team_name)
        container_info = docker_mgr.get_container_status(sanitized_name)
        
        if container_info:
            return jsonify({
                'success': True,
                'has_container': True,
                'status': container_info['status'],
                'webshell_url': container_info['webshell_url'],
                'created_at': container_info.get('created_at'),
                'expires_at': container_info.get('expires_at')
            })
        else:
            return jsonify({
                'success': True,
                'has_container': False
            })
            
    except Exception as e:
        logger.error(f"Error in status: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/create', methods=['POST'])
def api_create():
    """
    Create a new webshell container for a team
    """
    try:
        data = request.get_json()
        team_name = data.get('team_name', '').strip()
        username = data.get('username', '').strip()
        
        if not team_name:
            return jsonify({
                'success': False,
                'error': 'Team name is required'
            }), 400
        
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username is required'
            }), 400
        
        # Validate username format
        import re
        if not re.match(r'^[a-z0-9_-]{3,20}$', username):
            return jsonify({
                'success': False,
                'error': 'Invalid username format'
            }), 400
        
        sanitized_name = sanitize_team_name(team_name)
        
        # Check if container already exists
        existing = docker_mgr.get_container_status(sanitized_name)
        if existing:
            return jsonify({
                'success': True,
                'message': 'Container already exists',
                'webshell_url': existing['webshell_url']
            })
        
        # Create new container
        result = docker_mgr.create_container(
            team_name=sanitized_name,
            username=username
        )
        
        if result['success']:
            logger.info(f"Container created for team: {team_name}")
            return jsonify({
                'success': True,
                'message': 'Container created successfully',
                'webshell_url': result['webshell_url'],
                'container_id': result['container_id']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to create container')
            }), 500
            
    except Exception as e:
        logger.error(f"Error in create: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/delete', methods=['POST'])
def api_delete():
    """
    Stop and remove a team's webshell container
    """
    try:
        data = request.get_json()
        team_name = data.get('team_name', '').strip()
        
        if not team_name:
            return jsonify({
                'success': False,
                'error': 'Team name is required'
            }), 400
        
        sanitized_name = sanitize_team_name(team_name)
        result = docker_mgr.delete_container(sanitized_name)
        
        if result['success']:
            logger.info(f"Container deleted for team: {team_name}")
            return jsonify({
                'success': True,
                'message': 'Container stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to stop container')
            }), 500
            
    except Exception as e:
        logger.error(f"Error in delete: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/admin/list', methods=['GET'])
def api_admin_list():
    """
    Admin endpoint: List all active containers
    Requires API_SECRET header
    """
    auth = request.headers.get('X-API-Secret')
    if auth != API_SECRET:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        containers = docker_mgr.list_all_containers()
        return jsonify({
            'success': True,
            'containers': containers
        })
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/admin/cleanup', methods=['POST'])
def api_admin_cleanup():
    """
    Admin endpoint: Cleanup expired containers
    Requires API_SECRET header
    """
    auth = request.headers.get('X-API-Secret')
    if auth != API_SECRET:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        result = docker_mgr.cleanup_expired_containers()
        return jsonify({
            'success': True,
            'cleaned': result['cleaned'],
            'errors': result.get('errors', [])
        })
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Webshell API on port {port}")
    logger.info(f"CTFd URL: {CTFD_URL}")
    logger.info(f"Webshell Base URL: {WEBSHELL_BASE_URL}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
