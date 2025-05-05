"""
Utility functions for detecting and getting information about container environments.
"""
import os
import subprocess
from typing import Optional


def is_running_in_container() -> bool:
    """
    Detect if the application is running inside a container.
    
    Returns:
        bool: True if running in a container, False otherwise.
    """
    # Check for .dockerenv file
    if os.path.exists('/.dockerenv'):
        return True
    
    # Check for container-specific cgroup info
    try:
        with open('/proc/self/cgroup', 'r') as f:
            for line in f:
                if 'docker' in line or 'kubepods' in line:
                    return True
    except (IOError, FileNotFoundError):
        pass
    
    # Check for container-specific environment variables
    if os.environ.get('KUBERNETES_SERVICE_HOST') or os.environ.get('DOCKER_CONTAINER'):
        return True
    
    return False


def get_container_info() -> Optional[str]:
    """
    Get information about the container if running in one.
    
    Returns:
        Optional[str]: Container version, tag, or SHA if available, None otherwise.
    """
    if not is_running_in_container():
        return None
    
    # Try to get container info from environment variables
    container_info = os.environ.get('CONTAINER_VERSION') or os.environ.get('CONTAINER_TAG')
    if container_info:
        return container_info
    
    # Try to get git commit SHA if available
    git_sha = os.environ.get('GIT_COMMIT') or os.environ.get('GIT_SHA')
    if git_sha:
        return f"Git SHA: {git_sha}"
    
    # Try to get container ID
    try:
        container_id = subprocess.check_output(['cat', '/proc/self/cgroup'], text=True)
        if container_id:
            # Extract the container ID from cgroup info
            for line in container_id.splitlines():
                if 'docker' in line:
                    parts = line.split('/')
                    if len(parts) > 2:
                        return f"Container ID: {parts[-1]}"
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return "Running in container, but no version information available"