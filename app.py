from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import jenkins
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
import re
import requests
from requests.auth import HTTPBasicAuth
import time
import google.generativeai as genai
import base64
import json
from urllib.parse import urlparse
import tempfile
import subprocess
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
CORS(app)

# Jenkins configuration
JENKINS_URL = os.getenv('JENKINS_URL', 'http://localhost:8080')
JENKINS_USERNAME = os.getenv('JENKINS_USERNAME', 'admin')
JENKINS_PASSWORD = os.getenv('JENKINS_PASSWORD', 'admin')

# Gemini AI configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini AI configured successfully")
else:
    print("⚠️ GEMINI_API_KEY not found in environment variables")

# Initialize Jenkins server
try:
    jenkins_server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
    info = jenkins_server.get_info()
    print("Successfully connected to Jenkins")
    print(f"[DEBUG] Jenkins info: {info}")
except Exception as e:
    print(f"[ERROR] Failed to connect to Jenkins: {e}")
    import traceback
    traceback.print_exc()
    jenkins_server = None

# FIXED: Enhanced required plugins list with all dependencies
REQUIRED_PLUGINS = {
    'pipeline': [
        'workflow-aggregator',     # Main pipeline plugin (includes most dependencies)
        'workflow-api',           # Pipeline API
        'workflow-job',           # Pipeline Job
        'workflow-support',       # Pipeline Support
        'workflow-step-api',      # Pipeline Step API
        'workflow-durable-task-step',  # Durable Task Step
        'workflow-scm-step',      # SCM Step
        'workflow-cps',           # Pipeline Groovy
        'workflow-basic-steps',   # Basic Steps
        'pipeline-stage-view',    # Stage View
        'structs',               # Structs (required dependency)
        'script-security',       # Script Security (required)
        'scm-api',              # SCM API (required)
        'credentials',          # Credentials (required)
        'durable-task',        # Durable Task (required)
    ],
    'multibranch': [
        'workflow-aggregator',
        'workflow-api',
        'workflow-job',
        'workflow-support', 
        'workflow-multibranch',
        'branch-api',
        'scm-api',
        'structs',
        'credentials',
        'git'  # Git plugin often required
    ],
    'freestyle': ['git', 'credentials'],  # ENHANCED: Added Git support for freestyle
    'external': [],
    'matrix': ['git', 'credentials'],     # ENHANCED: Added Git support for matrix
    'folder': ['cloudbees-folder'],
    'organization': [
        'github-branch-source',
        'branch-api',
        'scm-api',
        'workflow-multibranch',
        'structs',
        'credentials'
    ]
}

def get_jenkins_crumb():
    """Get Jenkins CSRF crumb for API requests (Jenkins 2.440+)"""
    try:
        crumb_url = f"{JENKINS_URL}/crumbIssuer/api/json"
        response = requests.get(
            crumb_url,
            auth=HTTPBasicAuth(JENKINS_USERNAME, JENKINS_PASSWORD),
            timeout=10
        )
        if response.status_code == 200:
            crumb_data = response.json()
            return {crumb_data['crumbRequestField']: crumb_data['crumb']}
        else:
            print(f"[DEBUG] No CSRF protection or crumb not available: {response.status_code}")
            return {}
    except Exception as e:
        print(f"[DEBUG] Error getting CSRF crumb: {e}")
        return {}

def check_plugins_via_api():
    """Check plugins using REST API instead of python-jenkins"""
    try:
        headers = get_jenkins_crumb()
        headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        plugins_url = f"{JENKINS_URL}/pluginManager/api/json?depth=1"
        response = requests.get(
            plugins_url,
            auth=HTTPBasicAuth(JENKINS_USERNAME, JENKINS_PASSWORD),
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            plugins = {plugin['shortName']: plugin for plugin in data.get('plugins', [])}
            return plugins
        else:
            print(f"[ERROR] Failed to get plugins via API: {response.status_code}")
            return {}
    except Exception as e:
        print(f"[ERROR] Error checking plugins via API: {e}")
        return {}

def check_required_plugins(job_type):
    """Enhanced plugin checking with REST API fallback"""
    if not jenkins_server:
        return False, "Jenkins server not connected"
    
    required = REQUIRED_PLUGINS.get(job_type, [])
    if not required:
        return True, "No plugins required"
    
    try:
        # First try using python-jenkins
        try:
            plugins_info = jenkins_server.get_plugins_info()
            installed_plugins = {plugin['shortName']: plugin for plugin in plugins_info}
            print(f"[DEBUG] Using python-jenkins plugin check")
        except:
            # Fallback to REST API
            installed_plugins = check_plugins_via_api()
            print(f"[DEBUG] Using REST API plugin check")
        
        missing_plugins = []
        disabled_plugins = []
        
        for plugin_name in required:
            if plugin_name not in installed_plugins:
                missing_plugins.append(plugin_name)
            elif not installed_plugins[plugin_name].get('enabled', False):
                disabled_plugins.append(plugin_name)
        
        if missing_plugins or disabled_plugins:
            error_msg = []
            if missing_plugins:
                error_msg.append(f"Missing: {', '.join(missing_plugins)}")
            if disabled_plugins:
                error_msg.append(f"Disabled: {', '.join(disabled_plugins)}")
            return False, "; ".join(error_msg)
        
        return True, "All required plugins are installed and enabled"
        
    except Exception as e:
        print(f"[ERROR] Error checking plugins: {e}")
        return False, f"Error checking plugins: {str(e)}"

def install_plugins_via_api(plugin_list):
    """Install plugins using Jenkins REST API with CSRF protection"""
    try:
        headers = get_jenkins_crumb()
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        # Use the newer plugin installation endpoint
        install_url = f"{JENKINS_URL}/pluginManager/install"
        
        # Format plugins for installation
        plugin_data = []
        for plugin in plugin_list:
            plugin_data.append(f"plugin.{plugin}.default=on")
        
        post_data = "&".join(plugin_data)
        
        response = requests.post(
            install_url,
            auth=HTTPBasicAuth(JENKINS_USERNAME, JENKINS_PASSWORD),
            headers=headers,
            data=post_data,
            timeout=30
        )
        
        if response.status_code in [200, 302]:
            return True, f"Successfully initiated installation of plugins: {', '.join(plugin_list)}"
        else:
            return False, f"Failed to install plugins. Status code: {response.status_code}, Response: {response.text[:200]}"
            
    except Exception as e:
        print(f"[ERROR] Error installing plugins via API: {e}")
        return False, f"Error installing plugins: {str(e)}"

def install_missing_plugins(job_type):
    """Enhanced plugin installation with better error handling"""
    if not jenkins_server:
        return False, "Jenkins server not connected"
    
    required = REQUIRED_PLUGINS.get(job_type, [])
    if not required:
        return True, "No plugins required"
    
    try:
        # Check which plugins are actually missing
        installed_plugins = check_plugins_via_api()
        if not installed_plugins:
            # Fallback to python-jenkins
            try:
                plugins_info = jenkins_server.get_plugins_info()
                installed_plugins = {plugin['shortName']: plugin for plugin in plugins_info}
            except:
                return False, "Cannot access plugin information"
        
        missing_plugins = []
        for plugin_name in required:
            if plugin_name not in installed_plugins:
                missing_plugins.append(plugin_name)
        
        if not missing_plugins:
            return True, "All plugins already installed"
        
        print(f"[INFO] Installing missing plugins for {job_type}: {missing_plugins}")
        
        # Try installing via REST API
        success, message = install_plugins_via_api(missing_plugins)
        if success:
            return True, f"{message}. Please restart Jenkins to complete installation."
        else:
            return False, f"Plugin installation failed: {message}"
            
    except Exception as e:
        print(f"[ERROR] Error in install_missing_plugins: {e}")
        return False, f"Error installing plugins: {str(e)}"

def _detect_job_type(job_class: str) -> str:
    """Map Jenkins internal _class to a human-readable job type."""
    if job_class == "hudson.model.FreeStyleProject":
        return "freestyle"
    if job_class == "org.jenkinsci.plugins.workflow.job.WorkflowJob":
        return "pipeline"
    if job_class == "org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject":
        return "multibranch"
    if job_class == "hudson.model.ExternalJob":
        return "external"
    if job_class == "hudson.matrix.MatrixProject":
        return "matrix"
    if job_class == "com.cloudbees.hudson.plugins.folder.Folder":
        return "folder"
    if job_class == "jenkins.branch.OrganizationFolder":
        return "organization"
    return "unknown"

def _parse_job_config_xml(config_xml: str, job_type: str) -> dict:
    """ENHANCED: Parse Jenkins job configuration XML with SCM support"""
    try:
        root = ET.fromstring(config_xml)
        config_data = {}
        
        # Get description
        desc_elem = root.find('description')
        config_data['description'] = desc_elem.text if desc_elem is not None and desc_elem.text else ''
        
        if job_type == 'freestyle':
            # ENHANCED: Parse freestyle project configuration with SCM support
            builders = root.find('builders')
            if builders is not None:
                # Check for Shell command (Unix/Linux)
                shell_task = builders.find('hudson.tasks.Shell')
                if shell_task is not None:
                    command_elem = shell_task.find('command')
                    config_data['build_steps'] = command_elem.text if command_elem is not None and command_elem.text else ''
                    config_data['build_step_type'] = 'shell'
                else:
                    # Check for Batch command (Windows)
                    batch_task = builders.find('hudson.tasks.BatchFile')
                    if batch_task is not None:
                        command_elem = batch_task.find('command')
                        config_data['build_steps'] = command_elem.text if command_elem is not None and command_elem.text else ''
                        config_data['build_step_type'] = 'batch'
                    else:
                        # Default to shell if no build step found
                        config_data['build_steps'] = ''
                        config_data['build_step_type'] = 'shell'
            else:
                # Default values if no builders section
                config_data['build_steps'] = ''
                config_data['build_step_type'] = 'shell'
            
            # NEW: Parse SCM configuration for freestyle jobs
            scm = root.find('scm')
            if scm is not None:
                scm_class = scm.get('class', '')
                if 'GitSCM' in scm_class:
                    config_data['scm_type'] = 'git'
                    
                    # Parse Git configuration
                    remote_config = scm.find('.//hudson.plugins.git.UserRemoteConfig')
                    if remote_config is not None:
                        url_elem = remote_config.find('url')
                        config_data['repository_url'] = url_elem.text if url_elem is not None and url_elem.text else ''
                        
                        credentials_elem = remote_config.find('credentialsId')
                        config_data['credentials_id'] = credentials_elem.text if credentials_elem is not None and credentials_elem.text else ''
                    
                    # Parse branch specifier
                    branch_spec = scm.find('.//hudson.plugins.git.BranchSpec/name')
                    if branch_spec is not None and branch_spec.text:
                        config_data['branch_specifier'] = branch_spec.text
                    else:
                        config_data['branch_specifier'] = '*/master'
                    
                    # Parse repository browser
                    browser = scm.find('browser')
                    if browser is not None:
                        browser_class = browser.get('class', '')
                        config_data['repository_browser'] = browser_class.split('.')[-1] if browser_class else 'auto'
                    else:
                        config_data['repository_browser'] = 'auto'
                else:
                    config_data['scm_type'] = 'none'
            else:
                config_data['scm_type'] = 'none'
                config_data['repository_url'] = ''
                config_data['credentials_id'] = ''
                config_data['branch_specifier'] = '*/master'
                config_data['repository_browser'] = 'auto'
                    
        elif job_type == 'pipeline':
            # Parse pipeline configuration (existing code)
            definition = root.find('definition')
            if definition is not None:
                definition_class = definition.get('class', '')
                
                if 'CpsFlowDefinition' in definition_class:
                    config_data['pipeline_definition_type'] = 'script'
                    script_elem = definition.find('script')
                    config_data['pipeline_script'] = script_elem.text if script_elem is not None and script_elem.text else ''
                    
                elif 'CpsScmFlowDefinition' in definition_class:
                    config_data['pipeline_definition_type'] = 'scm'
                    
                    scm = definition.find('scm')
                    if scm is not None:
                        remote_config = scm.find('.//hudson.plugins.git.UserRemoteConfig')
                        if remote_config is not None:
                            url_elem = remote_config.find('url')
                            config_data['repository_url'] = url_elem.text if url_elem is not None and url_elem.text else ''
                            
                            credentials_elem = remote_config.find('credentialsId')
                            config_data['credentials_id'] = credentials_elem.text if credentials_elem is not None and credentials_elem.text else ''
                        
                        branch_spec = scm.find('.//hudson.plugins.git.BranchSpec/name')
                        if branch_spec is not None and branch_spec.text:
                            branch_text = branch_spec.text
                            config_data['branch'] = branch_text.replace('*/', '') if branch_text.startswith('*/') else branch_text
                    
                    script_path_elem = definition.find('scriptPath')
                    config_data['script_path'] = script_path_elem.text if script_path_elem is not None and script_path_elem.text else 'Jenkinsfile'
                    
        elif job_type == 'multibranch':
            # Parse multibranch pipeline configuration (existing code)
            sources = root.find('sources')
            if sources is not None:
                git_source = sources.find('.//jenkins.plugins.git.GitSCMSource')
                if git_source is not None:
                    remote_elem = git_source.find('remote')
                    config_data['repository_url'] = remote_elem.text if remote_elem is not None and remote_elem.text else ''
                    
                    id_elem = git_source.find('id')
                    config_data['repo_id'] = id_elem.text if id_elem is not None and id_elem.text else ''
                    
        elif job_type == 'matrix':
            # ENHANCED: Parse matrix project configuration with SCM support
            axes = root.find('axes')
            if axes is not None:
                text_axis = axes.find('hudson.matrix.TextAxis')
                if text_axis is not None:
                    name_elem = text_axis.find('name')
                    config_data['axis_name'] = name_elem.text if name_elem is not None and name_elem.text else ''
                    
                    values = text_axis.find('values')
                    if values is not None:
                        value_strings = [elem.text for elem in values.findall('string') if elem.text]
                        config_data['axis_values'] = ','.join(value_strings)
            
            # Get build steps
            builders = root.find('builders')
            if builders is not None:
                shell_task = builders.find('hudson.tasks.Shell')
                if shell_task is not None:
                    command_elem = shell_task.find('command')
                    config_data['build_steps'] = command_elem.text if command_elem is not None and command_elem.text else ''
            
            # NEW: Parse SCM configuration for matrix jobs
            scm = root.find('scm')
            if scm is not None:
                scm_class = scm.get('class', '')
                if 'GitSCM' in scm_class:
                    config_data['scm_type'] = 'git'
                    remote_config = scm.find('.//hudson.plugins.git.UserRemoteConfig')
                    if remote_config is not None:
                        url_elem = remote_config.find('url')
                        config_data['repository_url'] = url_elem.text if url_elem is not None and url_elem.text else ''
                        credentials_elem = remote_config.find('credentialsId')
                        config_data['credentials_id'] = credentials_elem.text if credentials_elem is not None and credentials_elem.text else ''
                    branch_spec = scm.find('.//hudson.plugins.git.BranchSpec/name')
                    config_data['branch_specifier'] = branch_spec.text if branch_spec is not None and branch_spec.text else '*/master'
                else:
                    config_data['scm_type'] = 'none'
            else:
                config_data['scm_type'] = 'none'
                    
        elif job_type == 'organization':
            # Parse organization folder configuration (existing code)
            navigators = root.find('navigators')
            if navigators is not None:
                github_navigator = navigators.find('org.jenkinsci.plugins.github_branch_source.GitHubSCMNavigator')
                if github_navigator is not None:
                    repo_owner_elem = github_navigator.find('repoOwner')
                    config_data['organization_name'] = repo_owner_elem.text if repo_owner_elem is not None and repo_owner_elem.text else ''
        
        return config_data
        
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return {}
    except Exception as e:
        print(f"Error extracting configuration: {e}")
        return {}

def _get_job_config_xml(job_type: str, job_data: dict) -> str:
    """ENHANCED: Generate Jenkins job configuration XML with SCM support"""
    
    def escape_xml(text):
        """Escape XML special characters"""
        if not text:
            return ''
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
    
    if job_type == 'freestyle':
        build_steps = escape_xml(job_data.get('build_steps', 'echo "Hello World"'))
        description = escape_xml(job_data.get('description', ''))
        build_step_type = job_data.get('build_step_type', 'shell')  # Default to shell
        
        # Choose the appropriate task type based on selection
        if build_step_type == 'batch':
            task_xml = f'''<hudson.tasks.BatchFile>
      <command>{build_steps}</command>
    </hudson.tasks.BatchFile>'''
        else:
            task_xml = f'''<hudson.tasks.Shell>
      <command>{build_steps}</command>
    </hudson.tasks.Shell>'''
        
        # NEW: Handle SCM configuration for freestyle jobs
        scm_type = job_data.get('scm_type', 'none')
        
        if scm_type == 'git':
            repository_url = escape_xml(job_data.get('repository_url', ''))
            credentials_id = escape_xml(job_data.get('credentials_id', ''))
            branch_specifier = escape_xml(job_data.get('branch_specifier', '*/master'))
            repository_browser = job_data.get('repository_browser', 'auto')
            
            scm_xml = f'''<scm class="hudson.plugins.git.GitSCM" plugin="git@latest">
    <configVersion>2</configVersion>
    <userRemoteConfigs>
      <hudson.plugins.git.UserRemoteConfig>
        <url>{repository_url}</url>
        {f'<credentialsId>{credentials_id}</credentialsId>' if credentials_id else ''}
      </hudson.plugins.git.UserRemoteConfig>
    </userRemoteConfigs>
    <branches>
      <hudson.plugins.git.BranchSpec>
        <name>{branch_specifier}</name>
      </hudson.plugins.git.BranchSpec>
    </branches>
    <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
    <submoduleCfg class="empty-list"/>
    <extensions/>
  </scm>'''
        else:
            scm_xml = '<scm class="hudson.scm.NullSCM"/>'
        
        return f'''<?xml version='1.1' encoding='UTF-8'?>
<project>
  <actions/>
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  {scm_xml}
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>false</concurrentBuild>
  <builders>
    {task_xml}
  </builders>
  <publishers/>
  <buildWrappers/>
</project>'''
    
    elif job_type == 'pipeline':
        # Pipeline job XML generation (existing code)
        description = escape_xml(job_data.get('description', ''))
        pipeline_definition_type = job_data.get('pipeline_definition_type', 'script')
        
        if pipeline_definition_type == 'scm':
            repository_url = escape_xml(job_data.get('repository_url', ''))
            branch = escape_xml(job_data.get('branch', 'main'))
            script_path = escape_xml(job_data.get('script_path', 'Jenkinsfile'))
            credentials_id = escape_xml(job_data.get('credentials_id', ''))
            
            definition_config = f'''<definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps@latest">
    <scm class="hudson.plugins.git.GitSCM" plugin="git@latest">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>{repository_url}</url>
          {f'<credentialsId>{credentials_id}</credentialsId>' if credentials_id else ''}
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>*/{branch}</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="empty-list"/>
      <extensions/>
    </scm>
    <scriptPath>{script_path}</scriptPath>
    <lightweight>true</lightweight>
  </definition>'''
        else:
            pipeline_script = escape_xml(job_data.get('pipeline_script', '''pipeline {
    agent any
    stages {
        stage('Hello') {
            steps {
                echo 'Hello World'
            }
        }
    }
}'''))
            
            definition_config = f'''<definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps@latest">
    <script>{pipeline_script}</script>
    <sandbox>true</sandbox>
  </definition>'''
        
        return f'''<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job@latest">
  <actions/>
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  {definition_config}
  <triggers/>
  <disabled>false</disabled>
</flow-definition>'''
    
    elif job_type == 'external':
        description = escape_xml(job_data.get('description', ''))
        
        return f'''<?xml version='1.1' encoding='UTF-8'?>
<hudson.model.ExternalJob>
  <actions/>
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <disabled>false</disabled>
</hudson.model.ExternalJob>'''
    
    elif job_type == 'matrix':
        # ENHANCED: Matrix job XML generation with SCM support
        description = escape_xml(job_data.get('description', ''))
        axis_name = escape_xml(job_data.get('axis_name', 'environment'))
        axis_values = job_data.get('axis_values', 'dev,test,prod').split(',')
        build_steps = escape_xml(job_data.get('build_steps', 'echo "Matrix build for $environment"'))
        
        axis_values_xml = ''.join([f'<string>{escape_xml(val.strip())}</string>' for val in axis_values])
        
        # Handle SCM configuration for matrix jobs
        scm_type = job_data.get('scm_type', 'none')
        
        if scm_type == 'git':
            repository_url = escape_xml(job_data.get('repository_url', ''))
            credentials_id = escape_xml(job_data.get('credentials_id', ''))
            branch_specifier = escape_xml(job_data.get('branch_specifier', '*/master'))
            
            scm_xml = f'''<scm class="hudson.plugins.git.GitSCM" plugin="git@latest">
    <configVersion>2</configVersion>
    <userRemoteConfigs>
      <hudson.plugins.git.UserRemoteConfig>
        <url>{repository_url}</url>
        {f'<credentialsId>{credentials_id}</credentialsId>' if credentials_id else ''}
      </hudson.plugins.git.UserRemoteConfig>
    </userRemoteConfigs>
    <branches>
      <hudson.plugins.git.BranchSpec>
        <name>{branch_specifier}</name>
      </hudson.plugins.git.BranchSpec>
    </branches>
    <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
    <submoduleCfg class="empty-list"/>
    <extensions/>
  </scm>'''
        else:
            scm_xml = '<scm class="hudson.scm.NullSCM"/>'
        
        return f'''<?xml version='1.1' encoding='UTF-8'?>
<hudson.matrix.MatrixProject>
  <actions/>
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  {scm_xml}
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>false</concurrentBuild>
  <builders>
    <hudson.tasks.Shell>
      <command>{build_steps}</command>
    </hudson.tasks.Shell>
  </builders>
  <publishers/>
  <buildWrappers/>
  <axes>
    <hudson.matrix.TextAxis>
      <name>{axis_name}</name>
      <values>
        {axis_values_xml}
      </values>
    </hudson.matrix.TextAxis>
  </axes>
  <runSequentially>false</runSequentially>
</hudson.matrix.MatrixProject>'''
    
    elif job_type == 'folder':
        description = escape_xml(job_data.get('description', ''))
        
        return f'''<?xml version='1.1' encoding='UTF-8'?>
<com.cloudbees.hudson.plugins.folder.Folder plugin="cloudbees-folder@latest">
  <actions/>
  <description>{description}</description>
  <properties/>
  <folderViews class="com.cloudbees.hudson.plugins.folder.views.DefaultFolderViewHolder">
    <views>
      <hudson.model.AllView>
        <owner class="com.cloudbees.hudson.plugins.folder.Folder" reference="../../../.."/>
        <name>all</name>
        <filterExecutors>false</filterExecutors>
        <filterQueue>false</filterQueue>
        <properties class="hudson.model.View$PropertyList"/>
      </hudson.model.AllView>
    </views>
    <tabBar class="hudson.views.DefaultViewsTabBar"/>
  </folderViews>
  <healthMetrics/>
</com.cloudbees.hudson.plugins.folder.Folder>'''
    
    elif job_type == 'multibranch':
        repository_url = escape_xml(job_data.get('repository_url', ''))
        description = escape_xml(job_data.get('description', ''))
        
        if not repository_url:
            return _get_job_config_xml('freestyle', job_data)
        
        return f'''<?xml version='1.1' encoding='UTF-8'?>
<org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject plugin="workflow-multibranch@latest">
  <actions/>
  <description>{description}</description>
  <properties/>
  <folderViews class="jenkins.branch.MultiBranchProjectViewHolder" plugin="branch-api@latest">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </folderViews>
  <healthMetrics/>
  <icon class="jenkins.branch.MetadataActionFolderIcon" plugin="branch-api@latest">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </icon>
  <orphanedItemStrategy class="com.cloudbees.hudson.plugins.folder.computed.DefaultOrphanedItemStrategy" plugin="cloudbees-folder@latest">
    <pruneDeadBranches>true</pruneDeadBranches>
    <daysToKeep>-1</daysToKeep>
    <numToKeep>-1</numToKeep>
  </orphanedItemStrategy>
  <triggers/>
  <disabled>false</disabled>
  <sources class="jenkins.branch.BranchSource" plugin="branch-api@latest">
    <source class="jenkins.plugins.git.GitSCMSource" plugin="git@latest">
      <id>git-repo</id>
      <remote>{repository_url}</remote>
      <credentialsId></credentialsId>
      <traits/>
    </source>
    <strategy class="jenkins.branch.DefaultBranchPropertyStrategy" plugin="branch-api@latest">
      <properties class="empty-list"/>
    </strategy>
  </sources>
  <factory class="org.jenkinsci.plugins.workflow.multibranch.WorkflowBranchProjectFactory" plugin="workflow-multibranch@latest">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
    <scriptPath>Jenkinsfile</scriptPath>
  </factory>
</org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>'''
    
    elif job_type == 'organization':
        description = escape_xml(job_data.get('description', ''))
        organization_name = escape_xml(job_data.get('organization_name', 'myorg'))
        
        return f'''<?xml version='1.1' encoding='UTF-8'?>
<jenkins.branch.OrganizationFolder plugin="branch-api@latest">
  <actions/>
  <description>{description}</description>
  <properties/>
  <folderViews class="jenkins.branch.MultiBranchProjectViewHolder" plugin="branch-api@latest">
    <owner class="jenkins.branch.OrganizationFolder" reference="../.."/>
  </folderViews>
  <healthMetrics/>
  <icon class="jenkins.branch.MetadataActionFolderIcon" plugin="branch-api@latest">
    <owner class="jenkins.branch.OrganizationFolder" reference="../.."/>
  </icon>
  <orphanedItemStrategy class="com.cloudbees.hudson.plugins.folder.computed.DefaultOrphanedItemStrategy" plugin="cloudbees-folder@latest">
    <pruneDeadBranches>true</pruneDeadBranches>
    <daysToKeep>-1</daysToKeep>
    <numToKeep>-1</numToKeep>
  </orphanedItemStrategy>
  <triggers/>
  <disabled>false</disabled>
  <navigators>
    <org.jenkinsci.plugins.github_branch_source.GitHubSCMNavigator plugin="github-branch-source@latest">
      <repoOwner>{organization_name}</repoOwner>
      <credentialsId></credentialsId>
      <traits/>
    </org.jenkinsci.plugins.github_branch_source.GitHubSCMNavigator>
  </navigators>
  <projectFactories>
    <org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProjectFactory plugin="workflow-multibranch@latest">
      <scriptPath>Jenkinsfile</scriptPath>
    </org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProjectFactory>
  </projectFactories>
</jenkins.branch.OrganizationFolder>'''
    
    else:
        return _get_job_config_xml('freestyle', job_data)

def create_job_via_api(job_name, config_xml):
    """Create job using Jenkins REST API with CSRF protection"""
    try:
        headers = get_jenkins_crumb()
        headers.update({
            'Content-Type': 'application/xml',
            'Accept': 'application/json'
        })
        
        create_url = f"{JENKINS_URL}/createItem?name={job_name}"
        
        response = requests.post(
            create_url,
            auth=HTTPBasicAuth(JENKINS_USERNAME, JENKINS_PASSWORD),
            headers=headers,
            data=config_xml,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            return True, "Job created successfully"
        else:
            return False, f"API Error {response.status_code}: {response.text[:500]}"
            
    except Exception as e:
        return False, f"Request failed: {str(e)}"
    
class GitHubRepoAnalyzer:
    """AI-powered GitHub repository analyzer using Gemini with support for 2.0+ models and cross-platform shell commands"""

    # Define supported models with their capabilities
    SUPPORTED_MODELS = {
        'gemini-2.5-pro': {
            'version': 2.5,
            'capabilities': ['enhanced_reasoning', 'multimodal', 'thinking'],
            'context_window': 1048576,
            'description': 'Most advanced reasoning model for complex tasks'
        },
        'gemini-2.5-flash': {
            'version': 2.5,
            'capabilities': ['cost_efficient', 'high_throughput', 'thinking'],
            'context_window': 1048576,
            'description': 'Best price-performance model with thinking capabilities'
        },
        'gemini-2.5-flash-lite': {
            'version': 2.5,
            'capabilities': ['cost_efficient', 'high_throughput'],
            'context_window': 1048576,
            'description': 'Most cost-efficient model with high throughput'
        },
        'gemini-2.0-flash': {
            'version': 2.0,
            'capabilities': ['multimodal_output', 'tool_use', 'fast'],
            'context_window': 1048576,
            'description': 'Next-gen features with speed and tool use'
        },
        'gemini-2.0-flash-lite': {
            'version': 2.0,
            'capabilities': ['cost_efficient', 'low_latency'],
            'context_window': 1048576,
            'description': 'Cost-efficient with low latency'
        }
    }

    def __init__(self, model_name=None, fallback_enabled=True):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for repository analysis")
        
        self.fallback_enabled = fallback_enabled
        self.model_name = self._select_optimal_model(model_name)
        self.model_info = self.SUPPORTED_MODELS.get(self.model_name, {})
        
        try:
            self.model = genai.GenerativeModel(self.model_name)
            print(f"[AI] Initialized with {self.model_name} - {self.model_info.get('description', '')}")
        except Exception as e:
            print(f"[AI] Warning: Failed to initialize {self.model_name}: {e}")
            if self.fallback_enabled:
                self.model_name, self.model = self._get_fallback_model()
            else:
                raise

    def _select_optimal_model(self, requested_model=None):
        """Select the best available model based on preference and availability"""
        # If specific model requested, validate it
        if requested_model:
            if requested_model in self.SUPPORTED_MODELS:
                return requested_model
            else:
                print(f"[AI] Warning: Requested model '{requested_model}' not supported")
        
        # Check environment variable for model preference
        env_model = os.getenv('GEMINI_MODEL')
        if env_model and env_model in self.SUPPORTED_MODELS:
            return env_model
        
        # Default priority order (newest and most capable first)
        priority_models = [
            'gemini-2.5-flash',     # Best balance of performance and cost
            'gemini-2.5-pro',       # Most advanced for complex tasks
            'gemini-2.0-flash',     # Good performance with tool use
            'gemini-2.5-flash-lite', # High throughput, cost-efficient
            'gemini-2.0-flash-lite'  # Fallback option
        ]
        
        # Return first available model from priority list
        for model in priority_models:
            if model in self.SUPPORTED_MODELS:
                return model
        
        # Final fallback
        return 'gemini-2.5-flash'

    def _get_fallback_model(self):
        """Get fallback model if primary model fails"""
        fallback_models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash-lite']
        for model_name in fallback_models:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"[AI] Fallback to {model_name}")
                return model_name, model
            except Exception as e:
                print(f"[AI] Fallback model {model_name} failed: {e}")
                continue
        raise ValueError("No working Gemini model found")

    def analyze_repository(self, repo_url, branch='main', env_shell_type='sh'):
        """Analyze GitHub repository with comprehensive structure analysis and environment support"""
        try:
            # Validate env_shell_type parameter
            if env_shell_type not in ['sh', 'bat', 'osascript']:
                env_shell_type = 'sh'  # Default fallback
            
            repo_info = self._parse_github_url(repo_url)
            if not repo_info:
                return None, "Invalid GitHub repository URL"
            
            repo_structure = self._fetch_comprehensive_repo_structure(repo_info, branch)
            if not repo_structure:
                return None, "Failed to fetch repository structure"
            
            analysis_result = self._analyze_with_ai(repo_structure, repo_info, env_shell_type)
            return analysis_result, None
            
        except Exception as e:
            print(f"Error analyzing repository: {e}")
            return None, str(e)

    def _sanitize_json_response(self, response_text):
        """Minimal sanitization - FIXED to prevent over-escaping"""
        try:
            import re
            # Only remove actual control characters, don't touch valid JSON
            sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', response_text)
            return sanitized
        except Exception as e:
            print(f"[AI] Error in minimal sanitization: {e}")
            return response_text


    def _parse_ai_response(self, response_text):
        """Parse AI response with enhanced fallback and better error handling - FIXED"""
        try:
            import json
            import re
            
            # Clean up the response text
            response_text = response_text.strip()
            print(f"[AI] Raw response length: {len(response_text)}")
            
            # Look for JSON block in the response - DON'T sanitize first
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                
                # Try parsing the raw JSON first - most likely to work
                try:
                    analysis = json.loads(json_text)
                    if isinstance(analysis, dict):
                        print(f"[AI] Successfully parsed raw JSON")
                        return analysis
                except json.JSONDecodeError as e:
                    print(f"[AI] Raw JSON parsing failed: {e}")
                    # Show the problematic part
                    print(f"[AI] JSON sample around error: {json_text[max(0, e.pos-50):e.pos+50]}")
                
                # Only if raw parsing fails, try basic cleanup
                try:
                    # MINIMAL cleanup - only remove obvious issues
                    cleaned_json = json_text
                    
                    # Remove control characters that break JSON
                    cleaned_json = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned_json)
                    
                    # Fix common trailing commas (but don't over-process)
                    cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)
                    
                    analysis = json.loads(cleaned_json)
                    if isinstance(analysis, dict):
                        print(f"[AI] Successfully parsed cleaned JSON")
                        return analysis
                        
                except json.JSONDecodeError as e:
                    print(f"[AI] Cleaned JSON parsing failed: {e}")
            
            # Enhanced Fallback: Look for pipeline block OR generate one
            print(f"[AI] JSON parsing failed completely, trying pipeline extraction...")
            
            # Try to find existing pipeline
            jenkinsfile_start = response_text.find('pipeline {')
            extracted_jenkinsfile = None
            
            if jenkinsfile_start != -1:
                # Find the end of the pipeline block
                brace_count = 0
                jenkinsfile_end = jenkinsfile_start
                for i, char in enumerate(response_text[jenkinsfile_start:]):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                    if brace_count == 0:
                        jenkinsfile_end = jenkinsfile_start + i + 1
                        break
                
                extracted_jenkinsfile = response_text[jenkinsfile_start:jenkinsfile_end]
                print(f"[AI] Extracted pipeline block: {len(extracted_jenkinsfile)} characters")
            
            # If no pipeline found, generate one from response content
            if not extracted_jenkinsfile or len(extracted_jenkinsfile) < 50:
                print(f"[AI] No valid pipeline block found, generating from response content...")
                extracted_jenkinsfile = self._generate_jenkinsfile_from_response(response_text, 'bat', '', 'main')
            
            return {
                "analysis": {
                    "project_type": "Python Application (Fallback)",
                    "build_system": "pip",
                    "dependencies": ["opencv-python", "dlib", "numpy"],
                    "test_framework": "auto-detected", 
                    "deployment_type": "script",
                    "recommended_tools": ["Python", "pip", "Git"],
                    "complexity": "simple",
                    "shell_environment": "bat"  # Ensure correct environment
                },
                "jenkinsfile": extracted_jenkinsfile,
                "explanation": "Generated from AI response with enhanced fallback parsing for Windows batch environment",
                "recommendations": ["Review and customize the pipeline", "Test in development environment", "Verify Python dependencies"]
            }
            
        except Exception as e:
            print(f"[AI] Complete parsing failure: {e}")
            return None


    def _fix_json_format(self, json_text):
        """Attempt to fix common JSON formatting issues"""
        import re
        
        try:
            # Fix common issues
            fixed = json_text
            
            # Remove trailing commas before closing braces/brackets
            fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
            
            # Fix unquoted property names (simple case)
            fixed = re.sub(r'(\w+)(\s*:\s*)', r'"\1"\2', fixed)
            
            # Fix single quotes to double quotes
            fixed = re.sub(r"'([^']*)'(\s*:\s*)", r'"\1"\2', fixed)
            fixed = re.sub(r'(\w+\s*:\s*)"([^"]*)"', r'\1"\2"', fixed)
            
            return fixed
        except Exception as e:
            print(f"[AI] JSON fixing failed: {e}")
            return json_text

    def _generate_jenkinsfile_from_response(self, response_text, env_shell_type='sh', repo_url='', branch='main'):
        """Generate a Jenkinsfile from AI response content with smart project-type defaults and environment variables"""
        
        # Build command wrapper based on environment
        def get_command_wrapper(env_type):
            if env_type == 'bat':
                return lambda c: f'bat "{c}"'
            elif env_type == 'osascript':
                return lambda c: f'osascript -e "{c}"'
            else:
                return lambda c: f'sh \'{c}\''
        
        cmd_wrapper = get_command_wrapper(env_shell_type)
        
        # Try to extract build commands from the response
        build_commands = []
        test_commands = []
        
        # Look for common build patterns in the response
        build_patterns = [
            r'npm install', r'yarn install', r'npm run build', r'yarn build',
            r'pip install', r'python -m pip install', r'pip install -r requirements\.txt',
            r'mvn clean install', r'mvn package', r'gradle build', r'./gradlew build',
            r'go build', r'cargo build', r'make build'
        ]
        
        test_patterns = [
            r'npm test', r'yarn test', r'npm run test',
            r'pytest', r'python -m pytest', r'mvn test',
            r'go test', r'cargo test'
        ]
        
        import re
        lines = response_text.split('\n')
        
        for line in lines:
            line_clean = line.strip()
            if line_clean:
                # Check for build commands
                for pattern in build_patterns:
                    if re.search(pattern, line_clean, re.IGNORECASE):
                        build_commands.append(line_clean.replace('`', '').replace('$', '').strip())
                
                # Check for test commands  
                for pattern in test_patterns:
                    if re.search(pattern, line_clean, re.IGNORECASE):
                        test_commands.append(line_clean.replace('`', '').replace('$', '').strip())
        
        # Remove duplicates while preserving order
        build_commands = list(dict.fromkeys(build_commands))[:3]
        test_commands = list(dict.fromkeys(test_commands))[:2]
        
        # NEW: If no commands found, detect project type and use defaults
        if not build_commands and not test_commands:
            print(f"[AI] No commands found in response, detecting project type for defaults...")
            project_defaults = self._detect_project_and_generate_defaults(response_text, env_shell_type)
            build_commands = project_defaults.get('build_commands', [])
            test_commands = project_defaults.get('test_commands', [])
            tools_section = project_defaults.get('tools_section', '')
        else:
            tools_section = ""
        
        # Generate environment section
        environment_section = f"""
        environment {{
            GIT_URL = '{repo_url or 'https://github.com/yourusername/your-repo.git'}'
            BRANCH = '{branch}'
        }}"""
        
        # Generate build stage
        build_stage = ""
        if build_commands:
            build_steps = "\n                ".join([cmd_wrapper(cmd) for cmd in build_commands])
            build_stage = f"""
            stage('Build') {{
                steps {{
                    {build_steps}
                }}
            }}"""
        
        # Generate test stage  
        test_stage = ""
        if test_commands:
            test_steps = "\n                ".join([cmd_wrapper(cmd) for cmd in test_commands])
            test_stage = f"""
            stage('Test') {{
                steps {{
                    script {{
                        try {{
                            {test_steps}
                        }} catch (Exception e) {{
                            echo 'Tests failed or not properly configured'
                        }}
                    }}
                }}
            }}"""
        
        # Generate complete Jenkinsfile
        jenkinsfile = f"""pipeline {{
        agent any{tools_section}
        {environment_section}
        
        stages {{
            stage('Checkout') {{
                steps {{
                    checkout scm
                    echo 'Repository checked out successfully'
                    echo "Cloning from: ${{env.GIT_URL}}"
                    echo "Branch: ${{env.BRANCH}}"
                }}
            }}{build_stage}{test_stage}
            
            stage('Archive Artifacts') {{
                steps {{
                    script {{
                        try {{
                            // Archive common build artifacts
                            def artifactPatterns = ['build/**/*', 'dist/**/*', 'target/**/*', '*.jar', '*.war', '*.py', '*.js']
                            for (pattern in artifactPatterns) {{
                                if (findFiles(glob: pattern).length > 0) {{
                                    archiveArtifacts artifacts: pattern, fingerprint: true, allowEmptyArchive: true
                                }}
                            }}
                        }} catch (Exception e) {{
                            echo "Artifact archiving failed: ${{e.message}}"
                        }}
                    }}
                }}
            }}
        }}
        
        post {{
            success {{
                echo 'Pipeline completed successfully using {env_shell_type} commands!'
            }}
            failure {{
                echo 'Pipeline failed. Check build commands and dependencies.'
            }}
            always {{
                echo 'Cleaning up workspace...'
                cleanWs()
            }}
        }}
    }}"""
        
        print(f"[AI] Generated {'default' if not build_commands and not test_commands else 'extracted'} Jenkinsfile for {env_shell_type} environment")
        return jenkinsfile

    def _detect_project_and_generate_defaults(self, response_text, env_shell_type='sh'):
        """Detect project type from response and generate default build commands"""
        response_lower = response_text.lower()
        
        # Project type detection patterns
        project_patterns = {
            'react': ['react', 'jsx', 'package.json', 'npm', 'yarn', 'create-react-app'],
            'vue': ['vue', 'vue.js', 'nuxt', '@vue'],
            'angular': ['angular', '@angular', 'ng serve', 'ng build'],
            'node': ['node.js', 'nodejs', 'express', 'package.json'],
            'python': ['python', 'pip', 'requirements.txt', 'django', 'flask', 'fastapi', '.py'],
            'java': ['java', 'maven', 'gradle', 'spring', 'pom.xml', 'build.gradle'],
            'go': ['golang', 'go build', 'go.mod', 'go run'],
            'rust': ['rust', 'cargo', 'cargo.toml'],
            'php': ['php', 'composer', 'laravel', 'symfony'],
            'dotnet': ['.net', 'dotnet', 'csharp', 'c#', 'nuget']
        }
        
        # Detect project type
        detected_type = 'generic'
        for project_type, patterns in project_patterns.items():
            if any(pattern in response_lower for pattern in patterns):
                detected_type = project_type
                break
        
        print(f"[AI] Detected project type: {detected_type}")
        
        # Generate default commands based on project type
        defaults = {
            'react': {
                'build_commands': ['npm install', 'npm run build'],
                'test_commands': ['npm test'],
                'tools_section': '\n    tools {\n        nodejs \'NodeJS\'\n    }'
            },
            'vue': {
                'build_commands': ['npm install', 'npm run build'],
                'test_commands': ['npm run test:unit'],
                'tools_section': '\n    tools {\n        nodejs \'NodeJS\'\n    }'
            },
            'angular': {
                'build_commands': ['npm install', 'ng build --prod'],
                'test_commands': ['ng test --watch=false'],
                'tools_section': '\n    tools {\n        nodejs \'NodeJS\'\n    }'
            },
            'node': {
                'build_commands': ['npm install'],
                'test_commands': ['npm test'],
                'tools_section': '\n    tools {\n        nodejs \'NodeJS\'\n    }'
            },
            'python': {
                'build_commands': ['pip install -r requirements.txt'],
                'test_commands': ['python -m pytest', 'python -m unittest discover'],
                'tools_section': ''
            },
            'java': {
                'build_commands': ['mvn clean compile', 'mvn package'],
                'test_commands': ['mvn test'],
                'tools_section': '\n    tools {\n        maven \'Maven\'\n        jdk \'JDK-11\'\n    }'
            },
            'go': {
                'build_commands': ['go mod download', 'go build'],
                'test_commands': ['go test ./...'],
                'tools_section': ''
            },
            'rust': {
                'build_commands': ['cargo build --release'],
                'test_commands': ['cargo test'],
                'tools_section': ''
            },
            'php': {
                'build_commands': ['composer install'],
                'test_commands': ['./vendor/bin/phpunit'],
                'tools_section': ''
            },
            'dotnet': {
                'build_commands': ['dotnet restore', 'dotnet build'],
                'test_commands': ['dotnet test'],
                'tools_section': ''
            },
            'generic': {
                'build_commands': ['echo "No specific build commands detected"', 'echo "Please customize this pipeline for your project"'],
                'test_commands': ['echo "Add your test commands here"'],
                'tools_section': ''
            }
        }
        
        return defaults.get(detected_type, defaults['generic'])



    def _parse_github_url(self, repo_url):
        """Parse GitHub repository URL and extract owner/repo information"""
        try:
            # Handle different GitHub URL formats
            if repo_url.endswith('.git'):
                repo_url = repo_url[:-4]
            
            # Parse URL
            from urllib.parse import urlparse
            parsed = urlparse(repo_url)
            if 'github.com' not in parsed.netloc.lower():
                return None
            
            # Extract path components
            path_parts = [part for part in parsed.path.strip('/').split('/') if part]
            if len(path_parts) < 2:
                return None
            
            return {
                'owner': path_parts[0],
                'repo': path_parts[1]
            }
            
        except Exception as e:
            print(f"Error parsing GitHub URL: {e}")
            return None

    def _fetch_comprehensive_repo_structure(self, repo_info, branch='main'):
        """ENHANCED: Comprehensive repository structure fetching with SSL fix"""
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            owner = repo_info['owner']
            repo = repo_info['repo']
            
            # Get repository information
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {}
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            print(f"[AI] Fetching comprehensive repository info: {repo_api_url}")
            
            import requests
            repo_response = requests.get(repo_api_url, headers=headers, timeout=10, verify=False)
            if repo_response.status_code == 404:
                return None
            elif repo_response.status_code != 200:
                print(f"[AI] GitHub API error: {repo_response.status_code}")
                return None
            
            repo_data = repo_response.json()
            
            # COMPREHENSIVE FILE ANALYSIS
            files = []
            directories = []
            key_files = {}
            readme_content = ""
            project_structure = {}
            
            # Fetch root directory contents
            contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
            contents_response = requests.get(contents_url, headers=headers, timeout=10, verify=False)
            
            if contents_response.status_code == 200:
                contents = contents_response.json()
                
                # PRIORITY 1: Find and analyze README files first
                readme_files = [item for item in contents if item['type'] == 'file' and
                              any(readme in item['name'].lower() for readme in ['readme', 'read_me'])]
                
                for readme_file in readme_files:
                    try:
                        print(f"[AI] Fetching README: {readme_file['name']}")
                        readme_response = requests.get(readme_file['download_url'], timeout=10, verify=False)
                        if readme_response.status_code == 200:
                            readme_content = readme_response.text
                            key_files[readme_file['name']] = readme_content
                            break  # Use first README found
                    except Exception as e:
                        print(f"[AI] Error fetching README {readme_file['name']}: {e}")
                
                # ENHANCED: Comprehensive file patterns for different project types
                important_file_patterns = [
                    # Configuration files
                    'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
                    'requirements.txt', 'pipfile', 'pipfile.lock', 'setup.py', 'pyproject.toml', 'setup.cfg',
                    'pom.xml', 'build.gradle', 'build.gradle.kts', 'gradle.properties', 'maven.xml',
                    'composer.json', 'composer.lock', 'go.mod', 'go.sum', 'cargo.toml', 'cargo.lock',
                    'pubspec.yaml', 'pubspec.lock', 'mix.exs', 'rebar.config', 'dune-project',
                    # Build and deployment files
                    'dockerfile', 'docker-compose.yml', 'docker-compose.yaml', 'makefile', 'cmake.txt',
                    'jenkinsfile', '.travis.yml', '.github/workflows', '.gitlab-ci.yml', 'azure-pipelines.yml',
                    'deploy.yml', 'deployment.yaml', 'k8s.yaml', 'kubernetes.yaml',
                    # Environment and config
                    '.env', '.env.example', '.env.local', '.env.production', 'config.json', 'config.yaml',
                    'app.config', 'web.config', 'settings.py', 'config.py', 'application.properties',
                    # Framework specific
                    'angular.json', 'vue.config.js', 'next.config.js', 'nuxt.config.js', 'svelte.config.js',
                    'webpack.config.js', 'rollup.config.js', 'vite.config.js', 'tsconfig.json', 'jsconfig.json',
                    'babel.config.js', '.babelrc', 'postcss.config.js', 'tailwind.config.js',
                    # Documentation and scripts
                    'readme.md', 'readme.txt', 'install.md', 'setup.md', 'usage.md', 'api.md',
                    'run.sh', 'start.sh', 'build.sh', 'deploy.sh', 'install.sh', 'setup.sh',
                    'run.bat', 'start.bat', 'build.bat', 'app.py', 'main.py', 'index.js', 'server.js',
                    # Testing
                    'jest.config.js', 'karma.conf.js', 'protractor.conf.js', 'cypress.json', 'playwright.config.js',
                    'pytest.ini', 'tox.ini', 'phpunit.xml', 'testng.xml'
                ]
                
                # Process all files and directories
                for item in contents:
                    if item['type'] == 'file':
                        files.append({'name': item['name'], 'size': item.get('size', 0), 'path': item['name']})
                        
                        # Check if it's an important file
                        file_name_lower = item['name'].lower()
                        if (file_name_lower in important_file_patterns or
                            any(pattern in file_name_lower for pattern in important_file_patterns)):
                            try:
                                print(f"[AI] Fetching important file: {item['name']}")
                                file_response = requests.get(item['download_url'], timeout=10, verify=False)
                                if file_response.status_code == 200:
                                    content = file_response.text[:3000]  # Increased content size
                                    key_files[item['name']] = content
                            except Exception as e:
                                print(f"[AI] Error fetching {item['name']}: {e}")
                    
                    elif item['type'] == 'dir':
                        directories.append(item['name'])
            
            # Get programming languages
            languages_url = f"https://api.github.com/repos/{owner}/{repo}/languages"
            languages_response = requests.get(languages_url, headers=headers, timeout=10, verify=False)
            languages = languages_response.json() if languages_response.status_code == 200 else {}
            
            # ENHANCED: Project analysis based on README and structure
            project_analysis = self._analyze_project_from_readme_and_structure(readme_content, key_files, files, languages)
            
            return {
                'repo_info': {
                    'name': repo_data.get('name', ''),
                    'description': repo_data.get('description', ''),
                    'language': repo_data.get('language', ''),
                    'size': repo_data.get('size', 0),
                    'topics': repo_data.get('topics', []),
                    'default_branch': repo_data.get('default_branch', 'main'),
                    'has_issues': repo_data.get('has_issues', False),
                    'has_projects': repo_data.get('has_projects', False),
                    'has_wiki': repo_data.get('has_wiki', False),
                    'forks_count': repo_data.get('forks_count', 0),
                    'stars_count': repo_data.get('stargazers_count', 0)
                },
                'files': files[:200],  # Increased file limit
                'directories': directories[:50],  # Increased directory limit
                'key_files': key_files,
                'languages': languages,
                'readme_content': readme_content,
                'project_structure': project_structure,
                'project_analysis': project_analysis  # NEW: Pre-analysis based on README
            }
            
        except Exception as e:
            print(f"Error fetching repository structure: {e}")
            return None

    def _analyze_dependency_files(self, key_files, files, languages):
        """Enhanced analysis of dependency files for better build detection"""
        
        analysis = {
            'build_system': 'custom',
            'dependencies': [],
            'scripts': {},
            'tools': [],
            'test_framework': 'unknown',
            'deployment_type': 'static',
            'complexity': 'moderate',
            'primary_source': 'file_structure'
        }
        
        file_names_lower = [f.lower() for f in key_files.keys()]
        
        # Node.js/JavaScript Analysis
        if 'package.json' in key_files:
            analysis.update(self._analyze_package_json(key_files['package.json']))
            analysis['primary_source'] = 'package.json'
        
        # Python Analysis
        elif 'requirements.txt' in key_files:
            analysis.update(self._analyze_requirements_txt(key_files['requirements.txt']))
            analysis['primary_source'] = 'requirements.txt'
        elif 'pyproject.toml' in key_files:
            analysis.update(self._analyze_pyproject_toml(key_files['pyproject.toml']))
            analysis['primary_source'] = 'pyproject.toml'
        elif 'setup.py' in key_files:
            analysis.update(self._analyze_setup_py(key_files['setup.py']))
            analysis['primary_source'] = 'setup.py'
        
        # Java Analysis
        elif 'pom.xml' in key_files:
            analysis.update(self._analyze_pom_xml(key_files['pom.xml']))
            analysis['primary_source'] = 'pom.xml'
        elif any(f in file_names_lower for f in ['build.gradle', 'build.gradle.kts']):
            gradle_file = next((key_files[k] for k in key_files.keys() 
                              if k.lower() in ['build.gradle', 'build.gradle.kts']), '')
            analysis.update(self._analyze_gradle_file(gradle_file))
            analysis['primary_source'] = 'build.gradle'
        
        # Go Analysis
        elif 'go.mod' in key_files:
            analysis.update(self._analyze_go_mod(key_files['go.mod']))
            analysis['primary_source'] = 'go.mod'
        
        # Rust Analysis
        elif 'cargo.toml' in key_files:
            analysis.update(self._analyze_cargo_toml(key_files['cargo.toml']))
            analysis['primary_source'] = 'cargo.toml'
        
        # Docker Analysis
        if any(f in file_names_lower for f in ['dockerfile', 'docker-compose.yml']):
            analysis['deployment_type'] = 'container'
            analysis['tools'].append('Docker')
        
        # Language-based fallback
        if not analysis['dependencies'] and languages:
            analysis['dependencies'] = list(languages.keys()) if isinstance(languages, dict) else languages
            lang_key = list(languages.keys())[0] if isinstance(languages, dict) and languages else 'custom'
            analysis['build_system'] = lang_key.lower() if isinstance(lang_key, str) else 'custom'
        
        return analysis

    def _analyze_package_json(self, content):
        """Analyze package.json for Node.js projects"""
        try:
            import json
            pkg = json.loads(content)
            
            scripts = pkg.get('scripts', {})
            dependencies = list(pkg.get('dependencies', {}).keys())
            dev_dependencies = list(pkg.get('devDependencies', {}).keys())
            
            # Detect framework
            framework = 'node'
            if any(dep in dependencies + dev_dependencies for dep in ['react', '@types/react']):
                framework = 'react'
            elif any(dep in dependencies + dev_dependencies for dep in ['vue', '@vue/cli']):
                framework = 'vue'
            elif any(dep in dependencies + dev_dependencies for dep in ['@angular/core', '@angular/cli']):
                framework = 'angular'
            elif any(dep in dependencies + dev_dependencies for dep in ['next', '@next/core']):
                framework = 'nextjs'
            
            # Detect test framework
            test_framework = 'unknown'
            if any(dep in dev_dependencies for dep in ['jest', '@jest/core']):
                test_framework = 'jest'
            elif any(dep in dev_dependencies for dep in ['mocha', 'chai']):
                test_framework = 'mocha'
            elif any(dep in dev_dependencies for dep in ['cypress', '@cypress/core']):
                test_framework = 'cypress'
            
            return {
                'build_system': 'yarn' if 'yarn' in scripts.get('install', '') else 'npm',
                'dependencies': dependencies + dev_dependencies,
                'scripts': scripts,
                'test_framework': test_framework,
                'deployment_type': 'static' if framework in ['react', 'vue'] else 'server',
                'tools': ['Node.js', framework.title()],
                'complexity': 'complex' if len(dependencies) > 20 else 'moderate'
            }
        except:
            return {'build_system': 'npm', 'dependencies': [], 'tools': ['Node.js']}

    def _analyze_requirements_txt(self, content):
        """Analyze requirements.txt for Python projects - FIXED"""
        try:
            # Handle content properly
            if isinstance(content, list):
                lines = content
            else:
                lines = str(content).split('\n')
            
            dependencies = []
            for line in lines:
                if isinstance(line, str):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # FIXED: Extract package name before version specifiers
                        import re
                        # Use regex to extract package name before any version specifier
                        match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                        if match:
                            dep = match.group(1)
                            dependencies.append(dep)

            # Detect framework
            framework = 'python'
            test_framework = 'unknown'
            dep_lower = [d.lower() for d in dependencies]
            
            if 'django' in dep_lower:
                framework = 'django'
            elif 'flask' in dep_lower:
                framework = 'flask'
            elif 'fastapi' in dep_lower:
                framework = 'fastapi'
            
            if 'pytest' in dep_lower:
                test_framework = 'pytest'
            elif 'unittest' in dep_lower or 'nose' in dep_lower:
                test_framework = 'unittest'

            return {
                'build_system': 'pip',
                'dependencies': dependencies,
                'test_framework': test_framework,
                'deployment_type': 'server' if framework != 'python' else 'script',
                'tools': ['Python', framework.title()],
                'complexity': 'complex' if len(dependencies) > 15 else 'moderate'
            }

        except Exception as e:
            print(f"[AI] Error analyzing requirements.txt: {e}")
            return {'build_system': 'pip', 'dependencies': [], 'tools': ['Python']}


    def _analyze_pyproject_toml(self, content):
        """Analyze pyproject.toml for Python projects"""
        return {'build_system': 'poetry', 'dependencies': [], 'tools': ['Python', 'Poetry']}

    def _analyze_setup_py(self, content):
        """Analyze setup.py for Python projects"""
        return {'build_system': 'setuptools', 'dependencies': [], 'tools': ['Python', 'Setuptools']}

    def _analyze_pom_xml(self, content):
        """Analyze pom.xml for Maven projects"""
        return {'build_system': 'maven', 'dependencies': [], 'tools': ['Java', 'Maven']}

    def _analyze_gradle_file(self, content):
        """Analyze build.gradle for Gradle projects"""
        return {'build_system': 'gradle', 'dependencies': [], 'tools': ['Java', 'Gradle']}

    def _analyze_go_mod(self, content):
        """Analyze go.mod for Go projects"""
        return {'build_system': 'go', 'dependencies': [], 'tools': ['Go']}

    def _analyze_cargo_toml(self, content):
        """Analyze Cargo.toml for Rust projects"""
        return {'build_system': 'cargo', 'dependencies': [], 'tools': ['Rust', 'Cargo']}

    def _analyze_project_from_readme_and_structure(self, readme_content, key_files, files, languages):
        """Analyze project type and build requirements from README and file structure"""
        
        analysis = {
            'detected_commands': {
                'install': [],
                'build': [],
                'test': [],
                'run': [],
                'deploy': []
            },
            'detected_technologies': [],
            'project_type': 'unknown',
            'has_dependencies_file': False,
            'entry_points': [],
            'framework': 'none'
        }
        
        # Analyze README content for build/run commands
        if readme_content:
            readme_lower = readme_content.lower()
            lines = readme_content.split('\n')
            
            # Look for installation/setup commands
            install_patterns = [
                r'pip install', r'npm install', r'yarn install', r'bundle install',
                r'composer install', r'go mod download', r'cargo build',
                r'mvn install', r'gradle build', r'make install'
            ]
            
            # Look for run commands
            run_patterns = [
                r'python\s+\w+\.py', r'node\s+\w+\.js', r'npm\s+start', r'yarn\s+start',
                r'java\s+-jar', r'go\s+run', r'cargo\s+run', r'mvn\s+spring-boot:run',
                r'./gradlew\s+bootRun', r'make\s+run', r'docker\s+run'
            ]
            
            # Look for build commands
            build_patterns = [
                r'npm\s+run\s+build', r'yarn\s+build', r'mvn\s+package', r'gradle\s+build',
                r'make\s+build', r'python\s+setup\.py\s+build', r'go\s+build', r'cargo\s+build'
            ]
            
            # Extract commands from README
            import re
            for line in lines:
                line_lower = line.lower().strip()
                # Look for code blocks and command indicators
                if any(indicator in line_lower for indicator in ['```', '$ ', '> ', '#']):
                    # Extract install commands
                    for pattern in install_patterns:
                        matches = re.findall(pattern, line_lower)
                        if matches:
                            analysis['detected_commands']['install'].append(line.strip())
                    
                    # Extract run commands
                    for pattern in run_patterns:
                        matches = re.findall(pattern, line_lower)
                        if matches:
                            analysis['detected_commands']['run'].append(line.strip())
                    
                    # Extract build commands
                    for pattern in build_patterns:
                        matches = re.findall(pattern, line_lower)
                        if matches:
                            analysis['detected_commands']['build'].append(line.strip())
        
        # Analyze file structure
        file_names = [f['name'].lower() for f in files]
        
        # Detect dependencies files
        dep_files = ['package.json', 'requirements.txt', 'pom.xml', 'build.gradle', 'composer.json', 'go.mod', 'cargo.toml']
        analysis['has_dependencies_file'] = any(dep_file in file_names for dep_file in dep_files)
        
        # Detect entry points
        entry_patterns = ['main.py', 'app.py', 'index.js', 'server.js', 'main.java', 'main.go', 'main.rs']
        analysis['entry_points'] = [f['name'] for f in files if f['name'].lower() in entry_patterns]
        
        # Detect technologies from files and README
        tech_indicators = {
            'react': ['package.json', 'react'],
            'vue': ['package.json', 'vue'],
            'angular': ['package.json', 'angular'],
            'django': ['manage.py', 'django'],
            'flask': ['app.py', 'flask'],
            'spring': ['pom.xml', 'spring'],
            'express': ['package.json', 'express'],
            'fastapi': ['main.py', 'fastapi'],
            'docker': ['dockerfile'],
            'kubernetes': ['.yaml', '.yml']
        }
        
        for tech, indicators in tech_indicators.items():
            if any(indicator in str(file_names) + readme_content.lower() for indicator in indicators):
                analysis['detected_technologies'].append(tech)
        
        # Determine project type based on analysis
        if 'react' in analysis['detected_technologies']:
            analysis['project_type'] = 'React Application'
            analysis['framework'] = 'react'
        elif 'vue' in analysis['detected_technologies']:
            analysis['project_type'] = 'Vue.js Application'
            analysis['framework'] = 'vue'
        elif 'angular' in analysis['detected_technologies']:
            analysis['project_type'] = 'Angular Application'
            analysis['framework'] = 'angular'
        elif 'django' in analysis['detected_technologies']:
            analysis['project_type'] = 'Django Application'
            analysis['framework'] = 'django'
        elif 'flask' in analysis['detected_technologies']:
            analysis['project_type'] = 'Flask Application'
            analysis['framework'] = 'flask'
        elif 'express' in analysis['detected_technologies']:
            analysis['project_type'] = 'Express API'
            analysis['framework'] = 'express'
        elif languages:
            main_lang = list(languages.keys()) if isinstance(languages, dict) and languages else 'Unknown'
            analysis['project_type'] = f'{main_lang} Application'
        
        return analysis

    def _analyze_with_ai(self, repo_structure, repo_info, env_shell_type='sh'):
        """Analyze repository with enhanced README-based analysis and environment support"""
        max_retries = 3
        base_delay = 33
        
        for attempt in range(max_retries):
            try:
                prompt = self._build_comprehensive_analysis_prompt(repo_structure, repo_info, env_shell_type)
                
                # Apply model-specific optimizations
                generation_config = self._get_model_config()
                if generation_config:
                    response = self.model.generate_content(prompt, generation_config=generation_config)
                else:
                    response = self.model.generate_content(prompt)
                
                if not response.text:
                    if attempt < max_retries - 1:
                        continue
                    return self._generate_intelligent_fallback_analysis(repo_structure, env_shell_type)
                
                analysis = self._parse_ai_response(response.text)
                
                # ENHANCED: Validate and enhance AI response
                if self._is_generic_response(analysis):
                    print(f"[AI] Generic response detected, enhancing with README analysis...")
                    analysis = self._enhance_with_readme_analysis(analysis, repo_structure, env_shell_type)
                
                return analysis
                
            except Exception as e:
                error_str = str(e).lower()
                print(f"[AI] Attempt {attempt + 1} failed: {e}")
                
                # Handle quota/rate limiting
                if any(keyword in error_str for keyword in ['quota', 'rate limit', '429', 'exceeded']):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[AI] Rate limit hit, retrying in {delay} seconds...")
                        time.sleep(delay)
                        continue
                
                # Handle model-specific errors
                if 'not found' in error_str or 'invalid model' in error_str:
                    if self.fallback_enabled and attempt == 0:
                        print(f"[AI] Model {self.model_name} not available, switching to fallback")
                        self.model_name, self.model = self._get_fallback_model()
                        continue
                
                # For final attempt or non-recoverable errors
                if attempt >= max_retries - 1:
                    print(f"[AI] Max retries exceeded, using intelligent fallback analysis")
                    return self._generate_intelligent_fallback_analysis(repo_structure, env_shell_type)
        
        return None

    def _build_comprehensive_analysis_prompt(self, repo_structure, repo_info, env_shell_type='sh'):
        """Build comprehensive analysis prompt with README-first approach and environment support"""
        
        # Extract key information
        languages = list(repo_structure['languages'].keys()) if repo_structure['languages'] else []
        main_language = repo_structure['repo_info']['language'] or (languages if languages else 'Unknown')
        readme_content = repo_structure.get('readme_content', '')
        project_analysis = repo_structure.get('project_analysis', {})
        
        # Build detailed file analysis
        key_files_summary = []
        for filename, content in repo_structure['key_files'].items():
            key_files_summary.append(f"- {filename}:\n  {content[:1000]}...")
        
        # FIXED: Safely handle directories with dicts
        dir_list = []
        for d in repo_structure['directories'][:20]:
            if isinstance(d, dict) and 'name' in d:
                dir_list.append(d['name'])
            elif isinstance(d, str):
                dir_list.append(d)
        
        # Environment-specific shell command instruction
        shell_instructions = {
            'sh': "Use 'sh' commands for Linux/Unix environments",
            'bat': "Use 'bat' commands for Windows environments",
            'osascript': "Use 'osascript' commands for macOS environments"
        }
        
        current_shell_instruction = shell_instructions.get(env_shell_type, shell_instructions['sh'])
        
        # Enhanced prompt with shell environment specification
        thinking_instruction = f"""
CRITICAL ANALYSIS APPROACH:
1. FIRST: Analyze the README file completely - this contains the actual build/run instructions
2. SECOND: Check for dependency files (package.json, requirements.txt, etc.) - but README takes priority
3. THIRD: If no README instructions, then detect from file structure and languages
4. FINAL: Generate pipeline with ACTUAL commands found in README, not assumptions

SHELL ENVIRONMENT: {env_shell_type.upper()}
{current_shell_instruction}

STRICT RULE: If README shows "python script.py" then use that, NOT "pip install -r requirements.txt" if no requirements.txt exists!
"""
        
        prompt = f"""
You are a senior DevOps engineer specializing in CI/CD pipeline creation. Analyze this GitHub repository by READING THE README FIRST to understand how to actually build/run this project.

{thinking_instruction}

TARGET ENVIRONMENT: {env_shell_type.upper()}
- For {env_shell_type} environment, use {env_shell_type} commands in the Jenkinsfile
- Examples: {env_shell_type} 'python main.py', {env_shell_type} 'npm install', etc.

REPOSITORY INFORMATION:
- Name: {repo_structure['repo_info']['name']}
- Description: {repo_structure['repo_info']['description']}
- Primary Language: {main_language}
- All Languages: {', '.join(languages)}
- Size: {repo_structure['repo_info']['size']} KB
- Topics: {', '.join(repo_structure['repo_info']['topics'])}

README CONTENT (MOST IMPORTANT - READ CAREFULLY):
{readme_content[:2000]}

PRE-ANALYSIS FROM README:
- Detected Install Commands: {project_analysis.get('detected_commands', {}).get('install', [])}
- Detected Run Commands: {project_analysis.get('detected_commands', {}).get('run', [])}
- Detected Build Commands: {project_analysis.get('detected_commands', {}).get('build', [])}
- Has Dependencies File: {project_analysis.get('has_dependencies_file', False)}
- Entry Points: {project_analysis.get('entry_points', [])}
- Project Type: {project_analysis.get('project_type', 'Unknown')}
- Technologies: {project_analysis.get('detected_technologies', [])}

PROJECT STRUCTURE:
Files: {', '.join([f['name'] for f in repo_structure['files'][:40]])}
Directories: {', '.join(dir_list)}

CONFIGURATION FILES CONTENT:
{chr(10).join(key_files_summary)}

BUILD STRATEGY REQUIREMENTS:
1. **PRIMARY**: Use commands found in README file - these are the authoritative build instructions
2. **SECONDARY**: If README doesn't specify, analyze dependency files (package.json, requirements.txt, etc.)
3. **FALLBACK**: Only use default commands if neither README nor config files provide guidance

SHELL COMMAND FORMAT:
- Use {env_shell_type} commands throughout the Jenkinsfile
- Example format: {env_shell_type} 'command here'

RESPONSE FORMAT (JSON):
{{
  "analysis": {{
    "project_type": "specific project type from README analysis",
    "build_system": "build tool determined from README/files",
    "dependencies": ["dependencies found in README or config files"],
    "test_framework": "test framework if mentioned in README or detected",
    "deployment_type": "deployment method from README or inferred",
    "recommended_tools": ["tools mentioned in README or needed"],
    "complexity": "simple|moderate|complex",
    "build_commands": ["ACTUAL commands from README or detected"],
    "test_commands": ["ACTUAL test commands from README or detected"],
    "run_commands": ["ACTUAL run commands from README"],
    "artifacts": ["build artifacts mentioned or inferred"],
    "readme_based": true,
    "shell_environment": "{env_shell_type}"
  }},
  "jenkinsfile": "complete Jenkinsfile using README-based commands with {env_shell_type} syntax",
  "explanation": "explanation focusing on README analysis and why these commands were chosen",
  "recommendations": ["specific recommendations based on README analysis"]
}}

CRITICAL: Base your Jenkinsfile on what the README actually says, and use {env_shell_type} command syntax throughout!
"""
        
        return prompt

    def _get_model_config(self):
        """Get model-specific generation configuration"""
        if self.model_info.get('version', 0) >= 2.5:
            # Enhanced configuration for 2.5+ models
            return genai.types.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=4096,
                response_mime_type="text/plain"
            )
        elif self.model_info.get('version', 0) >= 2.0:
            # Configuration for 2.0+ models
            return genai.types.GenerationConfig(
                temperature=0.2,
                top_p=0.9,
                top_k=50,
                max_output_tokens=3072
            )
        else:
            # Default configuration for older models
            return None

    def _is_generic_response(self, analysis):
        """Check if the AI response is too generic"""
        if not analysis or not isinstance(analysis, dict):
            return True
        
        jenkinsfile = analysis.get('jenkinsfile', '')
        
        # Check for generic placeholders
        generic_indicators = [
            'Add your build commands here',
            'echo "Build completed"',
            'echo "Tests completed"',
            '// Example:',
            'Add your test commands here',
            'Add your deployment commands here',
            'pip install -r requirements.txt'  # Generic when no requirements.txt exists
        ]
        
        return any(indicator in jenkinsfile for indicator in generic_indicators)

    def _enhance_with_readme_analysis(self, analysis, repo_structure, env_shell_type='sh'):
        """Enhance analysis using README content and project structure with environment support"""
        if not analysis:
            analysis = {}
        
        project_analysis = repo_structure.get('project_analysis', {})
        readme_content = repo_structure.get('readme_content', '')
        
        # Use README-detected commands if available
        detected_commands = project_analysis.get('detected_commands', {})
        if detected_commands.get('run'):
            # Generate Jenkinsfile based on README run commands
            run_commands = detected_commands['run']
            install_commands = detected_commands.get('install', [])
            build_commands = detected_commands.get('build', [])
            
            jenkinsfile = self._generate_readme_based_jenkinsfile(
                run_commands, install_commands, build_commands, repo_structure, env_shell_type
            )
            
            analysis['jenkinsfile'] = jenkinsfile
            analysis['explanation'] = f"Generated pipeline based on README instructions using {env_shell_type} commands. Detected commands: {run_commands}"
        else:
            # Fallback to smart analysis
            analysis = self._generate_intelligent_fallback_analysis(repo_structure, env_shell_type)
        
        return analysis

    def _generate_readme_based_jenkinsfile(self, run_commands, install_commands, build_commands, repo_structure, env_shell_type='sh'):
        """Generate Jenkinsfile based on README commands with environment-specific shell syntax and environment variables"""
        
        # Clean and prepare commands
        clean_run_commands = []
        clean_install_commands = []
        clean_build_commands = []
        
        # Clean README commands (remove markdown, backticks, etc.)
        import re
        for cmd in run_commands:
            clean_cmd = re.sub(r'[`$>&]', '', str(cmd)).strip()
            if clean_cmd and not clean_cmd.startswith('#'):
                clean_run_commands.append(clean_cmd)
        
        for cmd in install_commands:
            clean_cmd = re.sub(r'[`$>&]', '', str(cmd)).strip()
            if clean_cmd and not clean_cmd.startswith('#'):
                clean_install_commands.append(clean_cmd)
        
        for cmd in build_commands:
            clean_cmd = re.sub(r'[`$>&]', '', str(cmd)).strip()
            if clean_cmd and not clean_cmd.startswith('#'):
                clean_build_commands.append(clean_cmd)
        
        # Build command executor syntax based on environment
        def get_command_wrapper(env_type):
            if env_type == 'bat':
                return lambda c: f'bat "{c}"'
            elif env_type == 'osascript':
                return lambda c: f'osascript -e "{c}"'
            else: # default to sh
                return lambda c: f'sh \'{c}\''
        
        cmd_wrapper = get_command_wrapper(env_shell_type)
        
        # Extract repository info for environment variables
        repo_url = repo_structure.get('repo_info', {}).get('clone_url', 'https://github.com/yourusername/your-repo.git')
        if not repo_url or repo_url == 'https://github.com/yourusername/your-repo.git':
            # Try to construct from repo_info
            repo_info = repo_structure.get('repo_info', {})
            repo_name = repo_info.get('name', 'your-repo')
            # We don't have owner info here, so use a placeholder
            repo_url = f'https://github.com/yourusername/{repo_name}.git'
        
        default_branch = repo_structure.get('repo_info', {}).get('default_branch', 'main')
        
        # Determine project characteristics
        languages = repo_structure.get('languages', {})
        # FIXED: Handle languages properly
        if isinstance(languages, dict):
            main_language = list(languages.keys())[0].lower() if languages and list(languages.keys()) else 'unknown'  # ✅ CORRECT
        elif isinstance(languages, list):
            main_language = languages.lower() if languages and isinstance(languages, str) else 'unknown'  # ✅ CORRECT
        else:
            main_language = 'unknown'
        
        # Generate environment section
        environment_section = f"""
        environment {{
            GIT_URL = '{repo_url}'
            BRANCH = '{default_branch}'
        }}"""
        
        # Build install stage
        install_stage = ""
        if clean_install_commands:
            install_steps = "\n                ".join([cmd_wrapper(cmd) for cmd in clean_install_commands])
            install_stage = f"""
            stage('Install Dependencies') {{
                steps {{
                    {install_steps}
                }}
            }}"""
        
        # Build build stage
        build_stage = ""
        if clean_build_commands:
            build_steps = "\n                ".join([cmd_wrapper(cmd) for cmd in clean_build_commands])
            build_stage = f"""
            stage('Build') {{
                steps {{
                    {build_steps}
                }}
            }}"""
        
        # Build run/test stage based on run commands
        run_stage = ""
        if clean_run_commands:
            # For simple scripts, we might want to test they run without error
            run_steps = "\n                        ".join([cmd_wrapper(f'{cmd} --help || echo "Testing {cmd.split()[0] if cmd.split() else cmd} availability"') for cmd in clean_run_commands])
            run_stage = f"""
            stage('Validate') {{
                steps {{
                    script {{
                        echo 'Validating application can run...'
                        try {{
                            {run_steps}
                        }} catch (Exception e) {{
                            echo 'Validation failed or not properly configured'
                        }}
                    }}
                }}
            }}"""
        
        # Add language-specific tools if needed
        tools_section = ""
        if main_language in ['javascript', 'typescript'] or 'node' in str(clean_run_commands).lower():
            tools_section = """
        tools {
            nodejs 'NodeJS'
        }"""
        elif main_language == 'java':
            tools_section = """
        tools {
            jdk 'JDK-11'
            maven 'Maven'
        }"""
        
        # Generate comprehensive Jenkinsfile
        jenkinsfile = f"""pipeline {{
        agent any{tools_section}
        {environment_section}
        
        stages {{
            stage('Checkout') {{
                steps {{
                    checkout scm
                    echo 'Repository checked out successfully'
                    echo "Cloning from: ${{env.GIT_URL}}"
                    echo "Branch: ${{env.BRANCH}}"
                }}
            }}{install_stage}{build_stage}{run_stage}
            
            stage('Archive Artifacts') {{
                steps {{
                    script {{
                        // Archive relevant files based on project structure
                        try {{
                            if (fileExists('dist') || fileExists('build') || fileExists('target')) {{
                                if (fileExists('dist')) {{
                                    archiveArtifacts artifacts: 'dist/**/*', fingerprint: true, allowEmptyArchive: true
                                }}
                                if (fileExists('build')) {{
                                    archiveArtifacts artifacts: 'build/**/*', fingerprint: true, allowEmptyArchive: true
                                }}
                                if (fileExists('target')) {{
                                    archiveArtifacts artifacts: 'target/**/*', fingerprint: true, allowEmptyArchive: true
                                }}
                            }} else {{
                                // Archive source files for simple projects
                                archiveArtifacts artifacts: '*.py,*.js,*.java,*.go,*.rs,*.php', fingerprint: true, allowEmptyArchive: true
                            }}
                        }} catch (Exception e) {{
                            echo "Archiving failed: ${{e.message}}"
                        }}
                    }}
                }}
            }}
        }}
        
        post {{
            success {{
                echo 'Pipeline completed successfully! README-based build executed using {env_shell_type} commands.'
            }}
            failure {{
                echo 'Pipeline failed. Check README commands and dependencies.'
            }}
            always {{
                echo 'Cleaning up workspace...'
                cleanWs()
            }}
        }}
    }}"""
        
        return jenkinsfile




    def _generate_intelligent_fallback_analysis(self, repo_structure, env_shell_type='sh'):
        """Generate intelligent fallback analysis with enhanced dependency file analysis"""
        
        # ENHANCED: Safe data extraction with type checking
        def safe_get_languages(repo_structure):
            languages_data = repo_structure.get('languages', {})
            if isinstance(languages_data, list):
                return languages_data, languages_data if languages_data else 'Unknown'
            elif isinstance(languages_data, dict):
                lang_list = list(languages_data.keys()) if languages_data else []
                return lang_list, lang_list if lang_list else 'Unknown'
            else:
                return [], 'Unknown'
        
        def safe_get_dict(data, key, default=None):
            value = data.get(key, default or {})
            return value if isinstance(value, dict) else (default or {})
        
        def safe_get_list(data, key, default=None):
            value = data.get(key, default or [])
            return value if isinstance(value, list) else (default or [])
        
        # Extract data safely
        languages, main_language = safe_get_languages(repo_structure)
        key_files = safe_get_dict(repo_structure, 'key_files')
        project_analysis = safe_get_dict(repo_structure, 'project_analysis')
        readme_content = repo_structure.get('readme_content', '')
        files = safe_get_list(repo_structure, 'files')
        
        # ENHANCED: Deep dependency file analysis
        dependency_analysis = self._analyze_dependency_files(key_files, files, languages)
        
        # Determine project type with enhanced logic
        project_type = self._determine_project_type_enhanced(
            project_analysis, dependency_analysis, key_files, files, languages, readme_content
        )
        
        # Generate build commands with dependency analysis
        build_commands, test_commands, artifacts = self._generate_build_commands_enhanced(
            readme_content, dependency_analysis, key_files, files, languages, project_type
        )
        
        # Generate environment-specific Jenkinsfile
        if readme_content and project_analysis.get('detected_commands', {}).get('run'):
            jenkinsfile = self._generate_readme_based_jenkinsfile(
                project_analysis.get('detected_commands', {}).get('run', []),
                project_analysis.get('detected_commands', {}).get('install', []),
                project_analysis.get('detected_commands', {}).get('build', []),
                repo_structure,
                env_shell_type
            )
        else:
            repo_url = 'https://github.com/yourusername/your-repo.git'  # Default fallback
            branch = 'main'  # Default branch

            jenkinsfile = self._generate_structure_based_jenkinsfile(
                key_files, languages, build_commands, test_commands, env_shell_type, repo_url, branch
            )
        
        # Enhanced analysis result
        analysis = {
            "analysis": {
                "project_type": project_type,
                "build_system": dependency_analysis.get('build_system', 'custom'),
                "dependencies": dependency_analysis.get('dependencies', languages),
                "test_framework": dependency_analysis.get('test_framework', 'Auto-detected'),
                "deployment_type": dependency_analysis.get('deployment_type', 'Container/Static'),
                "recommended_tools": dependency_analysis.get('tools', ["Docker", "Git", "Jenkins"]),
                "complexity": dependency_analysis.get('complexity', 'moderate'),
                "build_commands": build_commands,
                "test_commands": test_commands,
                "run_commands": project_analysis.get('detected_commands', {}).get('run', []),
                "artifacts": artifacts,
                "readme_based": bool(readme_content and project_analysis.get('detected_commands', {}).get('run')),
                "shell_environment": env_shell_type,
                "dependency_analysis": dependency_analysis
            },
            "jenkinsfile": jenkinsfile,
            "explanation": f"Enhanced analysis for {project_type} using {env_shell_type} commands. " + (
                "Based on README and dependency file analysis." if readme_content 
                else f"Based on {dependency_analysis.get('primary_source', 'project structure')} analysis."
            ),
            "recommendations": self._generate_enhanced_recommendations(project_type, dependency_analysis, env_shell_type)
        }
        
        return analysis
    

    def _determine_project_type_enhanced(self, project_analysis, dependency_analysis, key_files, files, languages, readme_content):
        """Enhanced project type determination using multiple sources"""
        
        # Priority 1: Dependency file analysis
        if dependency_analysis.get('primary_source') != 'file_structure':
            deps = dependency_analysis.get('dependencies', [])
            if 'react' in [str(d).lower() for d in deps]:
                return 'React Application'
            elif 'django' in [str(d).lower() for d in deps]:
                return 'Django Application'
            elif 'flask' in [str(d).lower() for d in deps]:
                return 'Flask Application'
            elif 'spring-boot' in dependency_analysis.get('tools', []):
                return 'Spring Boot Application'
        
        # Priority 2: README analysis
        readme_type = project_analysis.get('project_type', '')
        if readme_type and readme_type != 'unknown':
            return readme_type
        
        # Priority 3: File structure analysis
        return self._detect_comprehensive_project_type(key_files, files, languages, readme_content)

    def _detect_comprehensive_project_type(self, key_files, files, languages, readme_content):
        """Comprehensive project type detection"""
        key_file_names = [f.lower() for f in key_files.keys()]
        file_names = [f['name'].lower() for f in files]
        readme_lower = readme_content.lower()
        
        # Framework detection patterns
        frameworks = {
            'React Application': ['react', 'jsx', 'create-react-app'],
            'Vue.js Application': ['vue', 'nuxt'],
            'Angular Application': ['angular', '@angular'],
            'Next.js Application': ['next.js', 'next.config'],
            'Express API': ['express', 'express.js'],
            'Django Application': ['django', 'manage.py', 'wsgi'],
            'Flask Application': ['flask', 'app.py', 'wsgi'],
            'FastAPI Application': ['fastapi', 'uvicorn'],
            'Spring Boot Application': ['spring-boot', 'spring'],
            'Go Application': ['main.go', 'go.mod'],
            'Rust Application': ['cargo.toml', 'src/main.rs'],
            'Python Script': ['main.py', 'app.py', '*.py'],
            'Node.js Application': ['package.json', 'node_modules'],
            'Java Application': ['*.java', 'pom.xml', '*.jar'],
            'Static Website': ['index.html', 'css', 'js'],
            'Docker Application': ['dockerfile', 'docker-compose'],
            'Library/Package': ['setup.py', 'lib/', 'src/']
        }
        
        # Check README content first
        for project_type, indicators in frameworks.items():
            if any(indicator in readme_lower for indicator in indicators):
                return project_type
        
        # Check package.json content for JavaScript frameworks
        if 'package.json' in key_files:
            package_content = key_files['package.json'].lower()
            for project_type, indicators in frameworks.items():
                if 'application' in project_type and any(indicator in package_content for indicator in indicators):
                    return project_type
        
        # Check file structure
        for project_type, indicators in frameworks.items():
            if any(indicator in str(file_names) + str(key_file_names) for indicator in indicators):
                return project_type
        
        # Language-based fallback
        if languages:
            main_lang = list(languages.keys()) if isinstance(languages, dict) and languages else languages if isinstance(languages, list) and languages else 'Unknown'
            return f'{main_lang} Application'
        
        return 'Generic Application'

    def _generate_build_commands_enhanced(self, readme_content, dependency_analysis, key_files, files, languages, project_type):
        """Generate build commands using enhanced dependency analysis"""
        
        build_commands = []
        test_commands = []
        artifacts = []
        
        build_system = dependency_analysis.get('build_system', 'custom')
        scripts = dependency_analysis.get('scripts', {})
        
        # Use dependency file analysis first
        if build_system == 'npm' or build_system == 'yarn':
            pkg_manager = build_system
            build_commands = [f'{pkg_manager} install']
            
            if 'build' in scripts:
                build_commands.append(f'{pkg_manager} run build')
            if 'test' in scripts:
                test_commands = [f'{pkg_manager} test']
            
            artifacts = ['build/**/*', 'dist/**/*', 'public/**/*']
        
        elif build_system == 'pip':
            build_commands = ['pip install -r requirements.txt']
            test_framework = dependency_analysis.get('test_framework', 'pytest')
            if test_framework == 'pytest':
                test_commands = ['python -m pytest']
            else:
                test_commands = ['python -m unittest discover']
            artifacts = ['**/*.py']
        
        elif build_system == 'maven':
            build_commands = ['mvn clean compile', 'mvn package']
            test_commands = ['mvn test']
            artifacts = ['target/*.jar', 'target/*.war']
        
        elif build_system == 'gradle':
            build_commands = ['./gradlew build']
            test_commands = ['./gradlew test']
            artifacts = ['build/libs/*.jar']
        
        # Fallback to existing logic
        if not build_commands:
            build_commands, test_commands, artifacts = self._detect_build_commands_from_structure(key_files, files, languages)
        
        return build_commands, test_commands, artifacts

    def _detect_build_commands_from_structure(self, key_files, files, languages):
        """Detect build commands from project structure"""
        key_file_names = [f.lower() for f in key_files.keys()]
        build_commands = []
        test_commands = []
        artifacts = []
        
        # Node.js projects
        if 'package.json' in key_file_names:
            has_yarn = 'yarn.lock' in key_file_names
            pkg_manager = 'yarn' if has_yarn else 'npm'
            build_commands = [f'{pkg_manager} install']
            
            # Check package.json for scripts
            package_content = key_files.get('package.json', '')
            if 'build' in package_content:
                build_commands.append(f'{pkg_manager} run build')
            if 'test' in package_content:
                test_commands = [f'{pkg_manager} test']
            
            artifacts = ['build/**/*', 'dist/**/*', 'public/**/*']
        
        # Python projects
        elif any(f in key_file_names for f in ['requirements.txt', 'setup.py', 'pyproject.toml']):
            if 'requirements.txt' in key_file_names:
                build_commands = ['pip install -r requirements.txt']
            elif 'pyproject.toml' in key_file_names:
                build_commands = ['pip install .']
            elif 'setup.py' in key_file_names:
                build_commands = ['pip install .']
            
            test_commands = ['python -m pytest', 'python -m unittest discover']
            artifacts = ['dist/*', '*.egg-info']
        
        # Java Maven projects
        elif 'pom.xml' in key_file_names:
            build_commands = ['mvn clean compile', 'mvn package']
            test_commands = ['mvn test']
            artifacts = ['target/*.jar', 'target/*.war']
        
        # Java Gradle projects
        elif any(f in key_file_names for f in ['build.gradle', 'build.gradle.kts']):
            build_commands = ['./gradlew build']
            test_commands = ['./gradlew test']
            artifacts = ['build/libs/*.jar']
        
        # Go projects
        elif 'go.mod' in key_file_names:
            build_commands = ['go mod download', 'go build']
            test_commands = ['go test ./...']
            artifacts = ['*']
        
        # Simple language-based detection
        elif languages:
            if isinstance(languages, dict):
                main_lang = list(languages.keys())[0].lower() if languages else 'unknown'
            elif isinstance(languages, list):
                main_lang = languages[0].lower() if languages else 'unknown'
            else:
                main_lang = 'unknown'
            
            if main_lang == 'python':
                # Look for main files
                python_files = [f['name'] for f in files if f['name'].endswith('.py')]
                if python_files:
                    main_file = next((f for f in python_files if 'main' in f.lower()), python_files[0])
                    build_commands = [f'python {main_file}']
            elif main_lang == 'java':
                build_commands = ['javac *.java']
                test_commands = ['java -cp . MainClass']
            elif main_lang == 'go':
                build_commands = ['go build']
                test_commands = ['go test']
        
        return build_commands, test_commands, artifacts

    def _generate_structure_based_jenkinsfile(self, key_files, languages, build_commands, test_commands, env_shell_type='sh', repo_url='', branch='main'):
        """Generate Jenkinsfile based on detected structure and build commands with environment-specific shell syntax and environment variables"""
        
        # Build command executor syntax based on environment
        def get_command_wrapper(env_type):
            if env_type == 'bat':
                return lambda c: f'bat "{c}"'
            elif env_type == 'osascript':
                return lambda c: f'osascript -e "{c}"'
            else: # default to sh
                return lambda c: f'sh \'{c}\''
        
        cmd_wrapper = get_command_wrapper(env_shell_type)
        
        # Generate environment section
        environment_section = f"""
        environment {{
            GIT_URL = '{repo_url or 'https://github.com/yourusername/your-repo.git'}'
            BRANCH = '{branch}'
        }}"""
        
        # Determine language-specific tools
        tools_section = ""
        if isinstance(languages, dict):
            main_language = list(languages.keys())[0].lower() if languages and list(languages.keys()) else 'unknown'
        elif isinstance(languages, list):
             main_language = languages.lower() if languages and isinstance(languages, str) else 'unknown' # ✅ CORRECT
        else:
            main_language = 'unknown'
        
        if main_language in ['javascript', 'typescript'] or 'package.json' in [f.lower() for f in key_files.keys()]:
            tools_section = """
        tools {
            nodejs 'NodeJS'
        }"""
        elif main_language == 'java':
            if 'pom.xml' in [f.lower() for f in key_files.keys()]:
                tools_section = """
        tools {
            maven 'Maven'
            jdk 'JDK-11'
        }"""
            elif any(f in [f.lower() for f in key_files.keys()] for f in ['build.gradle', 'build.gradle.kts']):
                tools_section = """
        tools {
            jdk 'JDK-11'
        }"""
        
        # Build stages based on detected commands
        build_stage = ""
        if build_commands:
            build_steps = "\n                ".join([cmd_wrapper(cmd) for cmd in build_commands])
            build_stage = f"""
            stage('Build') {{
                steps {{
                    {build_steps}
                }}
            }}"""
        
        test_stage = ""
        if test_commands:
            test_steps = "\n                        ".join([cmd_wrapper(cmd) for cmd in test_commands])
            test_stage = f"""
            stage('Test') {{
                steps {{
                    script {{
                        try {{
                            {test_steps}
                        }} catch (Exception e) {{
                            echo 'Tests failed or not properly configured'
                        }}
                    }}
                }}
            }}"""
        
        # Generate final Jenkinsfile
        jenkinsfile = f"""pipeline {{
        agent any{tools_section}
        {environment_section}
        
        stages {{
            stage('Checkout') {{
                steps {{
                    checkout scm
                    echo 'Repository checked out successfully'
                    echo "Cloning from: ${{env.GIT_URL}}"
                    echo "Branch: ${{env.BRANCH}}"
                }}
            }}{build_stage}{test_stage}
            
            stage('Archive Artifacts') {{
                steps {{
                    script {{
                        // Archive build artifacts if they exist
                        try {{
                            def artifactPatterns = ['build/**/*', 'dist/**/*', 'target/**/*', '*.jar', '*.war', '*.py', '*.js']
                            for (pattern in artifactPatterns) {{
                                if (findFiles(glob: pattern).length > 0) {{
                                    archiveArtifacts artifacts: pattern, fingerprint: true, allowEmptyArchive: true
                                }}
                            }}
                        }} catch (Exception e) {{
                            echo "Artifact archiving failed: ${{e.message}}"
                        }}
                    }}
                }}
            }}
        }}
        
        post {{
            success {{
                echo 'Pipeline completed successfully using {env_shell_type} commands!'
            }}
            failure {{
                echo 'Pipeline failed. Check build commands and dependencies.'
            }}
            always {{
                echo 'Cleaning up workspace...'
                cleanWs()
            }}
        }}
    }}"""
        
        return jenkinsfile


    def _generate_enhanced_recommendations(self, project_type, dependency_analysis, env_shell_type):
        """Generate enhanced recommendations based on comprehensive analysis"""
        
        recommendations = [
            f"Review the generated {project_type} pipeline for {env_shell_type} environment",
            f"Verify build commands match your {dependency_analysis.get('build_system', 'custom')} configuration"
        ]
        
        # Add specific recommendations based on analysis
        if dependency_analysis.get('test_framework') != 'unknown':
            recommendations.append(f"Consider adding {dependency_analysis['test_framework']} test reporting")
        
        if dependency_analysis.get('deployment_type') == 'container':
            recommendations.append("Add Docker build and deployment stages")
        
        if len(dependency_analysis.get('dependencies', [])) > 20:
            recommendations.append("Consider dependency caching for faster builds")
        
        recommendations.extend([
            "Add environment-specific configurations if needed",
            "Test the pipeline in a development environment first"
        ])
        
        return recommendations

    def get_model_info(self):
        """Get information about the current model"""
        return {
            'model_name': self.model_name,
            'version': self.model_info.get('version'),
            'capabilities': self.model_info.get('capabilities', []),
            'description': self.model_info.get('description', ''),
            'context_window': self.model_info.get('context_window')
        }


# Initialize GitHub analyzer
github_analyzer = GitHubRepoAnalyzer() if GEMINI_API_KEY else None

# NEW: AI Repository Analysis API Endpoints
@app.route('/api/ai/analyze-repository', methods=['POST'])
def analyze_repository():
    """Analyze GitHub repository with AI and generate Jenkinsfile with environment support"""
    try:
        if not github_analyzer:
            return jsonify({
                'success': False,
                'error': 'AI service not available. Please configure GEMINI_API_KEY.'
            })

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})

        repo_url = data.get('repository_url', '').strip()
        branch = data.get('branch', 'main').strip()
        env_shell_type = data.get('env_shell_type', 'sh').strip()  # GET ENVIRONMENT TYPE FROM REQUEST

        # Validate env_shell_type
        if env_shell_type not in ['sh', 'bat', 'osascript']:
            env_shell_type = 'sh'  # Default fallback

        if not repo_url:
            return jsonify({'success': False, 'error': 'Repository URL is required'})

        # Validate GitHub URL
        if 'github.com' not in repo_url.lower():
            return jsonify({'success': False, 'error': 'Only GitHub repositories are supported'})

        print(f"[AI] Analyzing repository: {repo_url} for {env_shell_type} environment")

        # Analyze repository with shell environment parameter
        analysis_result, error = github_analyzer.analyze_repository(repo_url, branch, env_shell_type)

        if error:
            return jsonify({'success': False, 'error': error})

        if not analysis_result:
            return jsonify({'success': False, 'error': 'Failed to analyze repository'})

        print(f"[AI] Analysis completed successfully for {env_shell_type} environment")

        return jsonify({
            'success': True,
            'analysis': analysis_result,
            'repository_url': repo_url,
            'branch': branch,
            'env_shell_type': env_shell_type  # RETURN ENVIRONMENT TYPE
        })

    except Exception as e:
        print(f"Error in analyze_repository: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'})


@app.route('/api/ai/create-pipeline-from-analysis', methods=['POST'])
def create_pipeline_from_analysis():
    """Create Jenkins pipeline job from AI analysis"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})

        # Extract required data
        job_name = data.get('job_name', '').strip()
        analysis = data.get('analysis', {})
        repository_url = data.get('repository_url', '').strip()
        branch = data.get('branch', 'main').strip()

        if not job_name:
            return jsonify({'success': False, 'error': 'Job name is required'})

        if not analysis or 'jenkinsfile' not in analysis:
            return jsonify({'success': False, 'error': 'Invalid analysis data'})

        # Validate job name
        if not re.match(r'^[a-zA-Z0-9_.-]+$', job_name):
            return jsonify({'success': False, 'error': 'Job name can only contain letters, numbers, underscores, dots, and hyphens'})

        # Check if job already exists
        try:
            jenkins_server.get_job_info(job_name)
            return jsonify({'success': False, 'error': f'Job "{job_name}" already exists'})
        except (jenkins.NotFoundException, jenkins.JenkinsException) as e:
            if "does not exist" in str(e):
                pass  # Job doesn't exist - expected for new job creation
            else:
                return jsonify({'success': False, 'error': f'Jenkins error: {str(e)}'})

        # ✅ FIXED: Extract the generated Jenkinsfile content and use script mode
        jenkinsfile_content = analysis['jenkinsfile']
        
        # Prepare job data for pipeline creation - USE SCRIPT MODE
        job_data = {
            'name': job_name,
            'type': 'pipeline', 
            'description': f'AI-generated pipeline for {repository_url}\n\nProject Type: {analysis.get("analysis", {}).get("project_type", "Unknown")}\nGenerated by Jenkins AI Assistant\n\nOriginal Repository: {repository_url}\nBranch: {branch}',
            'pipeline_definition_type': 'script',  # ✅ Use Pipeline script mode
            'pipeline_script': jenkinsfile_content,  # ✅ Embed the generated script directly
        }

        print(f"[AI] Creating pipeline job: {job_name} with embedded script")

        # Generate job configuration XML
        config_xml = _get_job_config_xml('pipeline', job_data)

        # Create the job
        try:
            jenkins_server.create_job(job_name, config_xml)
            print(f"[AI] Successfully created pipeline job: {job_name}")

            return jsonify({
                'success': True,
                'message': f'Pipeline job "{job_name}" created successfully with embedded script',
                'job_name': job_name,
                'job_type': 'pipeline',
                'pipeline_definition_type': 'script',  # ✅ Confirm it's using script mode
                'jenkinsfile': jenkinsfile_content,
                'analysis': analysis.get('analysis', {}),
                'explanation': analysis.get('explanation', ''),
                'recommendations': analysis.get('recommendations', []),
                'original_repository': repository_url,  # Keep reference to source repo
                'branch': branch
            })

        except Exception as e:
            error_msg = str(e).lower()
            if 'plugin' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Missing required Jenkins plugins for pipeline jobs. Please install Pipeline plugins and restart Jenkins.'
                })
            else:
                return jsonify({'success': False, 'error': f'Failed to create job: {str(e)}'})

    except Exception as e:
        print(f"Error in create_pipeline_from_analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Pipeline creation failed: {str(e)}'})


# NEW: Credentials API endpoint
@app.route('/api/credentials')
def get_credentials():
    """Get available Jenkins credentials (mock implementation for now)"""
    try:
        # This is a mock implementation
        # In a real implementation, you would query Jenkins credentials store
        credentials = [
            {'id': 'github-token', 'description': 'GitHub Personal Access Token'},
            {'id': 'gitlab-key', 'description': 'GitLab SSH Key'},
            {'id': 'bitbucket-oauth', 'description': 'Bitbucket OAuth Token'},
            {'id': 'docker-hub', 'description': 'Docker Hub Credentials'}
        ]
        return jsonify({'success': True, 'credentials': credentials})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

# [Keep all existing routes from the previous app.py - they remain unchanged]
# I'll include them all here for completeness...

@app.route('/api/jobs')
def get_jobs():
    """Get all Jenkins jobs with enhanced status information"""
    try:
        if jenkins_server:
            jobs = jenkins_server.get_jobs()
            jobs_with_type = []
            for job in jobs:
                try:
                    job_info = jenkins_server.get_job_info(job['name'])
                    job_class = job_info.get('_class', '')
                    job_type = _detect_job_type(job_class)
                    job_copy = dict(job)
                    job_copy['job_type'] = job_type
                    
                    # Add last build status information
                    if job_info.get('lastBuild'):
                        try:
                            last_build_info = jenkins_server.get_build_info(job['name'], job_info['lastBuild']['number'])
                            job_copy['result'] = last_build_info.get('result')
                            job_copy['building'] = last_build_info.get('building', False)
                            job_copy['timestamp'] = last_build_info.get('timestamp')
                            job_copy['duration'] = last_build_info.get('duration')
                        except Exception as e:
                            print(f"Error getting last build info for {job['name']}: {e}")
                    
                    jobs_with_type.append(job_copy)
                except Exception as e:
                    print(f"Error getting job info for {job['name']}: {e}")
                    job_copy = dict(job)
                    job_copy['job_type'] = 'unknown'
                    jobs_with_type.append(job_copy)
            return jsonify({'success': True, 'jobs': jobs_with_type})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/job/<job_name>/config')
def get_job_config(job_name):
    """Get job configuration for editing"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
        
        # Get job info to determine job type
        job_info = jenkins_server.get_job_info(job_name)
        job_class = job_info.get('_class', '')
        job_type = _detect_job_type(job_class)
        
        # Get job configuration XML
        config_xml = jenkins_server.get_job_config(job_name)
        
        # Parse configuration based on job type
        config_data = _parse_job_config_xml(config_xml, job_type)
        
        # Add basic job information
        config_data.update({
            'name': job_name,
            'job_type': job_type,
            'buildable': job_info.get('buildable', False),
            'disabled': not job_info.get('buildable', True)
        })
        
        return jsonify({
            'success': True,
            'config': config_data,
            'job_type': job_type
        })
        
    except jenkins.NotFoundException:
        return jsonify({'success': False, 'error': f'Job "{job_name}" not found'})
    except Exception as e:
        print(f"Error getting job config: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to get job configuration: {str(e)}'})

@app.route('/api/job/<job_name>/config/update', methods=['POST'])
def update_job_config(job_name):
    """Update job configuration with enhanced error handling"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No configuration data provided'})
        
        print(f"[DEBUG] Updating config for job: {job_name}")
        print(f"[DEBUG] Config data: {data}")
        
        # Validate job name
        if not job_name or job_name.strip() == '':
            return jsonify({'success': False, 'error': 'Invalid job name'})
        
        # Get current job type
        try:
            job_info = jenkins_server.get_job_info(job_name)
            job_class = job_info.get('_class', '')
            job_type = _detect_job_type(job_class)
            print(f"[DEBUG] Job type: {job_type}")
        except jenkins.NotFoundException:
            return jsonify({'success': False, 'error': f'Job "{job_name}" not found'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to get job info: {str(e)}'})
        
        # Check required plugins for job type
        plugins_ok, plugin_message = check_required_plugins(job_type)
        if not plugins_ok:
            return jsonify({'success': False, 'error': f'Plugin requirement not met: {plugin_message}'})
        
        # Validate job-type specific requirements
        if job_type == 'pipeline':
            pipeline_def_type = data.get('pipeline_definition_type', 'script')
            if pipeline_def_type == 'script' and not data.get('pipeline_script'):
                return jsonify({'success': False, 'error': 'Pipeline script is required'})
            elif pipeline_def_type == 'scm' and not data.get('repository_url'):
                return jsonify({'success': False, 'error': 'Repository URL is required for SCM-based pipelines'})
        
        elif job_type == 'multibranch' and not data.get('repository_url'):
            return jsonify({'success': False, 'error': 'Repository URL is required for multibranch projects'})
        
        elif job_type == 'organization' and not data.get('organization_name'):
            return jsonify({'success': False, 'error': 'Organization name is required'})
        
        # NEW: Validate SCM configuration for freestyle and matrix jobs
        if job_type in ['freestyle', 'matrix'] and data.get('scm_type') == 'git':
            if not data.get('repository_url'):
                return jsonify({'success': False, 'error': 'Repository URL is required for Git SCM'})
        
        # Generate updated configuration XML
        try:
            config_xml = _get_job_config_xml(job_type, data)
            print(f"[DEBUG] Generated XML config for {job_name}")
        except Exception as e:
            print(f"[ERROR] Failed to generate XML: {e}")
            return jsonify({'success': False, 'error': f'Failed to generate job configuration: {str(e)}'})
        
        # Update the job configuration
        try:
            jenkins_server.reconfig_job(job_name, config_xml)
            print(f"[DEBUG] Successfully updated job: {job_name}")
            
            return jsonify({
                'success': True,
                'message': f'Job "{job_name}" configuration updated successfully'
            })
            
        except Exception as e:
            print(f"[ERROR] Jenkins reconfig failed: {e}")
            error_msg = str(e)
            
            if 'plugin' in error_msg.lower():
                return jsonify({'success': False, 'error': 'Missing required Jenkins plugin. Please install the necessary plugins.'})
            elif 'xml' in error_msg.lower() or 'parse' in error_msg.lower():
                return jsonify({'success': False, 'error': 'Invalid configuration format. Please check your settings.'})
            elif 'permission' in error_msg.lower() or 'access' in error_msg.lower():
                return jsonify({'success': False, 'error': 'Permission denied. Check Jenkins user permissions.'})
            else:
                return jsonify({'success': False, 'error': f'Jenkins error: {error_msg}'})
        
    except Exception as e:
        print(f"[ERROR] Unexpected error updating job config: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Unexpected server error: {str(e)}'})

@app.route('/api/jobs/create', methods=['POST'])
def create_job():
    """FIXED: Create a new Jenkins job with enhanced error handling and API fallback"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        job_name = data.get('name', '').strip()
        job_type = data.get('type', 'freestyle')
        
        if not job_name:
            return jsonify({'success': False, 'error': 'Job name is required'})
        
        # Validate job name
        if not re.match(r'^[a-zA-Z0-9_.-]+$', job_name):
            return jsonify({'success': False, 'error': 'Job name can only contain letters, numbers, underscores, dots, and hyphens'})
        
        # Check if job already exists
        try:
            jenkins_server.get_job_info(job_name)
            return jsonify({'success': False, 'error': f'Job "{job_name}" already exists'})
        except jenkins.NotFoundException:
            pass
        except Exception as e:
            print(f"Error checking if job exists: {e}")

        # ENHANCED: Check required plugins with detailed reporting
        print(f"[INFO] Checking plugins for {job_type} job")
        plugins_ok, plugin_message = check_required_plugins(job_type)
        
        if not plugins_ok:
            print(f"[INFO] Plugin check failed: {plugin_message}")
            
            # Try to install missing plugins automatically
            install_ok, install_message = install_missing_plugins(job_type)
            if install_ok:
                return jsonify({
                    'success': False,
                    'error': f'Required plugins have been installed: {install_message}. Please restart Jenkins and try again.',
                    'restart_required': True
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Plugin requirements not met: {plugin_message}. Auto-installation failed: {install_message}. Please install the required plugins manually: {REQUIRED_PLUGINS.get(job_type, [])}',
                    'required_plugins': REQUIRED_PLUGINS.get(job_type, [])
                })
        
        print(f"[INFO] All required plugins available for {job_type}")
        
        # Validate job-type specific requirements
        if job_type == 'pipeline':
            pipeline_definition_type = data.get('pipeline_definition_type', 'script')
            if pipeline_definition_type == 'scm' and not data.get('repository_url'):
                return jsonify({'success': False, 'error': 'Repository URL is required for Pipeline script from SCM'})
            elif pipeline_definition_type == 'script' and not data.get('pipeline_script'):
                return jsonify({'success': False, 'error': 'Pipeline script is required for inline Pipeline script'})
        
        if job_type == 'multibranch' and not data.get('repository_url'):
            return jsonify({'success': False, 'error': 'Repository URL is required for multibranch projects'})
        
        if job_type == 'organization' and not data.get('organization_name'):
            return jsonify({'success': False, 'error': 'Organization name is required for organization folders'})
        
        # NEW: Validate SCM configuration for freestyle and matrix jobs
        if job_type in ['freestyle', 'matrix'] and data.get('scm_type') == 'git':
            if not data.get('repository_url'):
                return jsonify({'success': False, 'error': 'Repository URL is required for Git SCM'})
        
        # Generate job configuration XML
        try:
            config_xml = _get_job_config_xml(job_type, data)
            print(f"[DEBUG] Generated XML for {job_name} ({job_type}), length: {len(config_xml)}")
        except Exception as e:
            print(f"Error generating XML: {e}")
            return jsonify({'success': False, 'error': f'Failed to generate job configuration: {str(e)}'})
        
        # Try creating the job with python-jenkins first, then fallback to API
        try:
            jenkins_server.create_job(job_name, config_xml)
            print(f"[DEBUG] Successfully created job via python-jenkins: {job_name}")
            return jsonify({
                'success': True,
                'message': f'Job "{job_name}" created successfully',
                'job_name': job_name,
                'job_type': job_type,
                'method': 'python-jenkins'
            })
        except Exception as jenkins_error:
            print(f"[WARN] python-jenkins failed: {jenkins_error}")
            
            # Fallback to REST API
            try:
                api_success, api_message = create_job_via_api(job_name, config_xml)
                if api_success:
                    print(f"[DEBUG] Successfully created job via REST API: {job_name}")
                    return jsonify({
                        'success': True,
                        'message': f'Job "{job_name}" created successfully via REST API',
                        'job_name': job_name,
                        'job_type': job_type,
                        'method': 'rest-api'
                    })
                else:
                    raise Exception(f"Both methods failed. Jenkins: {jenkins_error}, API: {api_message}")
                    
            except Exception as api_error:
                print(f"[ERROR] Both creation methods failed: {api_error}")
                
                # Provide detailed error message
                error_msg = str(jenkins_error).lower()
                if 'plugin' in error_msg:
                    return jsonify({
                        'success': False, 
                        'error': f'Missing required Jenkins plugin for {job_type} job type. Required plugins: {REQUIRED_PLUGINS.get(job_type, [])}. Please install these plugins and restart Jenkins.',
                        'required_plugins': REQUIRED_PLUGINS.get(job_type, [])
                    })
                elif 'xml' in error_msg or 'parse' in error_msg:
                    return jsonify({'success': False, 'error': 'Invalid job configuration. Please check your settings.'})
                elif 'permission' in error_msg or 'access' in error_msg or '403' in error_msg:
                    return jsonify({'success': False, 'error': 'Permission denied. Check Jenkins user permissions and CSRF settings.'})
                else:
                    return jsonify({'success': False, 'error': f'Job creation failed: {str(api_error)}'})
        
    except Exception as e:
        print(f"Unexpected error creating job: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'})

# [Include all other existing routes from the original app.py]
# Plugin management endpoints
@app.route('/api/plugins/check/<job_type>')
def check_plugins_for_job_type(job_type):
    """Check if required plugins are installed for a job type"""
    try:
        plugins_ok, message = check_required_plugins(job_type)
        return jsonify({
            'success': True,
            'plugins_ok': plugins_ok,
            'message': message,
            'required_plugins': REQUIRED_PLUGINS.get(job_type, [])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/plugins/install/<job_type>', methods=['POST'])
def install_plugins_for_job_type(job_type):
    """Install missing plugins for a job type"""
    try:
        install_ok, message = install_missing_plugins(job_type)
        return jsonify({
            'success': install_ok,
            'message': message
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/jobs/<job_name>/delete', methods=['DELETE'])
def delete_job(job_name):
    """Delete a Jenkins job"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
        
        # Check if job exists
        try:
            jenkins_server.get_job_info(job_name)
        except jenkins.NotFoundException:
            return jsonify({'success': False, 'error': f'Job "{job_name}" does not exist'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error checking job: {str(e)}'})
        
        # Delete the job
        try:
            jenkins_server.delete_job(job_name)
            print(f"[DEBUG] Successfully deleted job: {job_name}")
            return jsonify({
                'success': True,
                'message': f'Job "{job_name}" deleted successfully'
            })
        except Exception as e:
            print(f"Error deleting job from Jenkins: {e}")
            return jsonify({'success': False, 'error': f'Jenkins error: {str(e)}'})
        
    except Exception as e:
        print(f"Unexpected error deleting job: {e}")
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'})

@app.route('/api/job/<job_name>')
def get_job_info(job_name):
    """Get detailed information about a specific job"""
    try:
        if jenkins_server:
            job_info = jenkins_server.get_job_info(job_name)
            job_info["job_type"] = _detect_job_type(job_info.get("_class", ""))
            return jsonify({"success": True, "job_info": job_info})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route("/api/job/<job_name>/type")
def get_job_type(job_name):
    """Return only the job type"""
    try:
        if not jenkins_server:
            return jsonify({"success": False, "error": "Jenkins server not connected"})
        job_info = jenkins_server.get_job_info(job_name)
        job_type = _detect_job_type(job_info.get("_class", ""))
        return jsonify({"success": True, "job_type": job_type})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/job/<job_name>/build', methods=['POST'])
def build_job(job_name):
    """Trigger a build for a specific job"""
    try:
        if jenkins_server:
            # Check if job is buildable
            job_info = jenkins_server.get_job_info(job_name)
            job_class = job_info.get('_class', '')
            
            # Some job types like folders and organization folders are not buildable
            non_buildable_types = [
                'com.cloudbees.hudson.plugins.folder.Folder',
                'jenkins.branch.OrganizationFolder'
            ]
            
            if job_class in non_buildable_types:
                return jsonify({'success': False, 'error': f'Job type "{_detect_job_type(job_class)}" is not buildable'})
            
            parameters = request.json.get('parameters', {}) if request.json else {}
            if parameters:
                jenkins_server.build_job(job_name, parameters=parameters)
            else:
                jenkins_server.build_job(job_name)
            return jsonify({'success': True, 'message': f'Build triggered for {job_name}'})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/job/<job_name>/builds')
def get_job_builds(job_name):
    """Get build history for a specific job with enhanced status information"""
    try:
        if jenkins_server:
            job_info = jenkins_server.get_job_info(job_name)
            builds = job_info.get('builds', [])
            
            # Enhance builds with detailed status information
            enhanced_builds = []
            for build in builds:
                try:
                    # Get detailed build info
                    detailed_build = jenkins_server.get_build_info(job_name, build['number'])
                    enhanced_build = {
                        'number': detailed_build.get('number'),
                        'url': detailed_build.get('url'),
                        'timestamp': detailed_build.get('timestamp'),
                        'duration': detailed_build.get('duration'),
                        'result': detailed_build.get('result'),  # SUCCESS, FAILURE, UNSTABLE, ABORTED, etc.
                        'building': detailed_build.get('building', False),
                        'color': job_info.get('color'),  # Job overall color
                        'displayName': detailed_build.get('displayName'),
                        'id': detailed_build.get('id'),
                        'keepLog': detailed_build.get('keepLog', False),
                        'queueId': detailed_build.get('queueId')
                    }
                    enhanced_builds.append(enhanced_build)
                except Exception as e:
                    print(f"Error getting detailed build info for build {build['number']}: {e}")
                    # Fallback to basic build info
                    enhanced_builds.append(build)
            
            return jsonify({'success': True, 'builds': enhanced_builds})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/job/<job_name>/build/<int:build_number>')
def get_build_info(job_name, build_number):
    """Get detailed information about a specific build"""
    try:
        if jenkins_server:
            build_info = jenkins_server.get_build_info(job_name, build_number)
            return jsonify({'success': True, 'build_info': build_info})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/job/<job_name>/build/<int:build_number>/console')
def get_build_console(job_name, build_number):
    """Get console output for a specific build"""
    try:
        if jenkins_server:
            console_output = jenkins_server.get_build_console_output(job_name, build_number)
            return jsonify({'success': True, 'console_output': console_output})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Nodes API Routes
@app.route('/api/nodes')
def get_nodes():
    """Get all Jenkins nodes with detailed information"""
    try:
        if jenkins_server:
            nodes = jenkins_server.get_nodes()
            detailed_nodes = []
            
            for node in nodes:
                try:
                    node_info = jenkins_server.get_node_info(node['name'])
                    node_copy = dict(node)
                    node_copy.update({
                        'executors': node_info.get('numExecutors', 0),
                        'offline': node_info.get('offline', False),
                        'offlineCause': node_info.get('offlineCause', None),
                        'temporarilyOffline': node_info.get('temporarilyOffline', False),
                        'monitorData': node_info.get('monitorData', {}),
                        'loadStatistics': node_info.get('loadStatistics', {}),
                    })
                    detailed_nodes.append(node_copy)
                except Exception as e:
                    print(f"Error getting node info for {node['name']}: {e}")
                    detailed_nodes.append(node)
            
            return jsonify({'success': True, 'nodes': detailed_nodes})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/nodes/<node_name>/toggle', methods=['POST'])
def toggle_node(node_name):
    """Toggle node online/offline status"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
        
        # Get current node info
        try:
            node_info = jenkins_server.get_node_info(node_name)
            is_offline = node_info.get('offline', False)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error getting node info: {str(e)}'})
        
        # Toggle node status
        try:
            if is_offline:
                jenkins_server.enable_node(node_name)
                message = f'Node "{node_name}" brought online'
            else:
                jenkins_server.disable_node(node_name, msg='Taken offline via dashboard')
                message = f'Node "{node_name}" taken offline'
            
            return jsonify({'success': True, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error toggling node: {str(e)}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'})

@app.route('/api/nodes/<node_name>/delete', methods=['DELETE'])
def delete_node(node_name):
    """Delete a Jenkins node"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
        
        if node_name == 'master' or node_name == 'built-in':
            return jsonify({'success': False, 'error': 'Cannot delete master/built-in node'})
        
        try:
            jenkins_server.delete_node(node_name)
            return jsonify({'success': True, 'message': f'Node "{node_name}" deleted successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error deleting node: {str(e)}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'})

# Queue API Routes
@app.route('/api/queue')
def get_queue():
    """Get build queue with detailed information"""
    try:
        if jenkins_server:
            queue = jenkins_server.get_queue_info()
            detailed_queue = []
            
            for item in queue:
                try:
                    queue_item = {
                        'id': item.get('id', 0),
                        'task': item.get('task', {}),
                        'why': item.get('why', 'Unknown reason'),
                        'inQueueSince': item.get('inQueueSince', 0),
                        'buildable': item.get('buildable', False),
                        'blocked': item.get('blocked', False),
                        'stuck': item.get('stuck', False),
                        'actions': item.get('actions', []),
                        'params': item.get('params', '')
                    }
                    detailed_queue.append(queue_item)
                except Exception as e:
                    print(f"Error processing queue item: {e}")
                    detailed_queue.append(item)
            
            return jsonify({'success': True, 'queue': detailed_queue})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/queue/<int:queue_id>/cancel', methods=['POST'])
def cancel_queue_item(queue_id):
    """Cancel a queued build"""
    try:
        if not jenkins_server:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
        
        try:
            jenkins_server.cancel_queue(queue_id)
            return jsonify({'success': True, 'message': f'Queue item {queue_id} cancelled successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error cancelling queue item: {str(e)}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'})

@app.route('/api/plugins')
def get_plugins():
    """Get installed plugins"""
    try:
        if jenkins_server:
            plugins = jenkins_server.get_plugins_info()
            return jsonify({'success': True, 'plugins': plugins})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/statistics')
def get_statistics():
    """Get Jenkins statistics"""
    try:
        if jenkins_server:
            info = jenkins_server.get_info()
            stats = {
                'total_jobs': len(jenkins_server.get_jobs()),
                'total_nodes': len(jenkins_server.get_nodes()),
                'total_plugins': len(jenkins_server.get_plugins_info()),
                'queue_size': len(jenkins_server.get_queue_info()),
                'jenkins_version': info.get('version', 'Unknown'),
                'uptime': info.get('upTime', 0)
            }
            return jsonify({'success': True, 'statistics': stats})
        else:
            return jsonify({'success': False, 'error': 'Jenkins server not connected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/git/repositories')
def get_git_repositories():
    """Get Git repositories (mock implementation)"""
    try:
        repositories = [
            {
                'name': 'main-app',
                'path': '/path/to/main-app',
                'branch': 'main',
                'status': 'clean',
                'lastCommit': 'abc123'
            },
            {
                'name': 'api-service',
                'path': '/path/to/api-service', 
                'branch': 'develop',
                'status': 'modified',
                'lastCommit': 'def456'
            }
        ]
        return jsonify({'success': True, 'repositories': repositories})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
