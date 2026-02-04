"""
Docker Manager for Webshell Containers
Handles container lifecycle: create, status, delete, cleanup
"""

import docker
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)


class DockerManager:
    """
    Manages Docker containers for webshell instances
    Each team gets one container with ttyd running
    """
    
    CONTAINER_PREFIX = 'webshell-'
    LABEL_TEAM = 'webshell.team'
    LABEL_USERNAME = 'webshell.username'
    LABEL_CREATED = 'webshell.created'
    LABEL_EXPIRES = 'webshell.expires'
    
    def __init__(
        self,
        network_name='webshell-network',
        image_name='webshell-instance:latest',
        memory_limit='512m',
        cpu_limit=0.5,
        timeout_hours=24,
        webshell_base_url='https://webshell.nullbytez.live'
    ):
        self.client = docker.from_env()
        self.network_name = network_name
        self.image_name = image_name
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout_hours = timeout_hours
        self.webshell_base_url = webshell_base_url
        
        # Ensure network exists
        self._ensure_network()
    
    def _ensure_network(self):
        """Ensure the webshell network exists"""
        try:
            self.client.networks.get(self.network_name)
            logger.info(f"Network {self.network_name} already exists")
        except docker.errors.NotFound:
            logger.info(f"Creating network {self.network_name}")
            self.client.networks.create(
                self.network_name,
                driver='bridge'
            )
    
    def _get_container_name(self, team_name):
        """Generate container name from team name"""
        return f"{self.CONTAINER_PREFIX}{team_name}"
    
    def _get_container(self, team_name):
        """Get container by team name, returns None if not found"""
        container_name = self._get_container_name(team_name)
        try:
            return self.client.containers.get(container_name)
        except docker.errors.NotFound:
            return None
    
    def get_container_status(self, team_name):
        """
        Get status of a team's container
        Returns dict with status info or None if no container
        """
        container = self._get_container(team_name)
        
        if not container:
            return None
        
        labels = container.labels
        created_at = labels.get(self.LABEL_CREATED, '')
        expires_at = labels.get(self.LABEL_EXPIRES, '')
        username = labels.get(self.LABEL_USERNAME, 'user')
        
        # Get the ttyd port mapping
        webshell_url = f"{self.webshell_base_url}/{team_name}"
        
        return {
            'container_id': container.short_id,
            'status': container.status,
            'team_name': team_name,
            'username': username,
            'webshell_url': webshell_url,
            'created_at': created_at,
            'expires_at': expires_at
        }
    
    def create_container(self, team_name, username='user'):
        """
        Create a new webshell container for a team
        """
        container_name = self._get_container_name(team_name)
        
        # Check if already exists
        existing = self._get_container(team_name)
        if existing:
            if existing.status != 'running':
                existing.start()
            webshell_url = f"{self.webshell_base_url}/{team_name}"
            return {
                'success': True,
                'container_id': existing.short_id,
                'webshell_url': webshell_url,
                'message': 'Container already exists'
            }
        
        try:
            now = datetime.utcnow()
            expires = now + timedelta(hours=self.timeout_hours)
            
            # Create container with ttyd
            container = self.client.containers.run(
                self.image_name,
                name=container_name,
                detach=True,
                network=self.network_name,
                mem_limit=self.memory_limit,
                cpu_quota=int(self.cpu_limit * 100000),
                cpu_period=100000,
                environment={
                    'USERNAME': username,
                    'TEAM_NAME': team_name
                },
                labels={
                    self.LABEL_TEAM: team_name,
                    self.LABEL_USERNAME: username,
                    self.LABEL_CREATED: now.isoformat(),
                    self.LABEL_EXPIRES: expires.isoformat()
                },
                restart_policy={'Name': 'unless-stopped'},
                # Security options
                cap_drop=['ALL'],
                cap_add=['CHOWN', 'SETUID', 'SETGID', 'DAC_OVERRIDE', 'FOWNER'],
                security_opt=['no-new-privileges:true'],
                # Resource limits
                pids_limit=100,
                # Don't expose ports directly - use traefik/nginx reverse proxy
            )
            
            webshell_url = f"{self.webshell_base_url}/{team_name}"
            
            logger.info(f"Created container {container_name} for team {team_name}")
            
            return {
                'success': True,
                'container_id': container.short_id,
                'webshell_url': webshell_url
            }
            
        except docker.errors.ImageNotFound:
            logger.error(f"Image {self.image_name} not found")
            return {
                'success': False,
                'error': 'Webshell image not found. Please contact admin.'
            }
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            return {
                'success': False,
                'error': f'Failed to create container: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating container: {e}")
            return {
                'success': False,
                'error': 'Internal error creating container'
            }
    
    def delete_container(self, team_name, force=True):
        """
        Stop and remove a team's container
        """
        container = self._get_container(team_name)
        
        if not container:
            return {
                'success': True,
                'message': 'Container does not exist'
            }
        
        try:
            container.stop(timeout=10)
            container.remove(force=force)
            logger.info(f"Deleted container for team {team_name}")
            return {
                'success': True,
                'message': 'Container stopped and removed'
            }
        except docker.errors.APIError as e:
            logger.error(f"Error deleting container: {e}")
            return {
                'success': False,
                'error': f'Failed to delete container: {str(e)}'
            }
    
    def list_all_containers(self):
        """
        List all webshell containers
        """
        containers = self.client.containers.list(
            all=True,
            filters={'name': self.CONTAINER_PREFIX}
        )
        
        result = []
        for container in containers:
            labels = container.labels
            result.append({
                'container_id': container.short_id,
                'name': container.name,
                'status': container.status,
                'team_name': labels.get(self.LABEL_TEAM, 'unknown'),
                'username': labels.get(self.LABEL_USERNAME, 'unknown'),
                'created_at': labels.get(self.LABEL_CREATED, ''),
                'expires_at': labels.get(self.LABEL_EXPIRES, '')
            })
        
        return result
    
    def cleanup_expired_containers(self):
        """
        Remove containers that have expired
        """
        containers = self.client.containers.list(
            all=True,
            filters={'name': self.CONTAINER_PREFIX}
        )
        
        now = datetime.utcnow()
        cleaned = []
        errors = []
        
        for container in containers:
            expires_str = container.labels.get(self.LABEL_EXPIRES, '')
            
            if not expires_str:
                continue
            
            try:
                expires = datetime.fromisoformat(expires_str)
                
                if now > expires:
                    team_name = container.labels.get(self.LABEL_TEAM, 'unknown')
                    try:
                        container.stop(timeout=10)
                        container.remove(force=True)
                        cleaned.append(team_name)
                        logger.info(f"Cleaned up expired container for team {team_name}")
                    except Exception as e:
                        errors.append({
                            'team': team_name,
                            'error': str(e)
                        })
            except ValueError:
                continue
        
        return {
            'cleaned': cleaned,
            'errors': errors
        }
    
    def restart_container(self, team_name):
        """
        Restart a team's container
        """
        container = self._get_container(team_name)
        
        if not container:
            return {
                'success': False,
                'error': 'Container does not exist'
            }
        
        try:
            container.restart(timeout=10)
            return {
                'success': True,
                'message': 'Container restarted'
            }
        except docker.errors.APIError as e:
            logger.error(f"Error restarting container: {e}")
            return {
                'success': False,
                'error': f'Failed to restart container: {str(e)}'
            }
