# Jenkins UI - Alternative Interface

A modern, responsive web-based alternative interface for Jenkins built with Python Flask and Bootstrap. This application provides a clean, user-friendly interface to interact with your Jenkins server while maintaining all the core functionality.

## Features

### 🎯 Core Functionality
- **Dashboard**: Overview with statistics and recent jobs
- **Job Management**: View, build, stop, and delete jobs
- **Build History**: Complete build history with console output
- **Node Management**: View and monitor build nodes
- **Queue Monitoring**: Real-time build queue status
- **Plugin Management**: View installed plugins

### 🎨 Modern UI/UX
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Modern Interface**: Clean, intuitive design with Bootstrap 5
- **Real-time Updates**: Auto-refresh functionality
- **Interactive Modals**: Detailed job information and build parameters
- **Status Indicators**: Color-coded build status badges
- **Console Output**: Syntax-highlighted build logs

### 🔧 Technical Features
- **RESTful API**: Complete API for all Jenkins operations
- **Error Handling**: Comprehensive error handling and user feedback
- **Security**: Environment-based configuration
- **Scalable**: Modular architecture for easy extension

## Screenshots

The interface includes:
- **Dashboard**: Statistics cards and recent jobs overview
- **Jobs List**: Complete job management with action buttons
- **Job Details**: Modal with tabs for info, builds, and console
- **Nodes View**: Build node status and information
- **Queue Monitor**: Real-time build queue status
- **Plugins List**: Installed plugins overview

## Installation

### Prerequisites
- Python 3.7 or higher
- Jenkins server running and accessible
- Jenkins credentials (username/password)

### Setup Instructions

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd jenkins-ui
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` file with your Jenkins configuration:
   ```env
   JENKINS_URL=http://your-jenkins-server:8080
   JENKINS_USERNAME=your-username
   JENKINS_PASSWORD=your-password
   SECRET_KEY=your-secret-key-here
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JENKINS_URL` | Jenkins server URL | `http://localhost:8080` |
| `JENKINS_USERNAME` | Jenkins username | `admin` |
| `JENKINS_PASSWORD` | Jenkins password | `admin` |
| `SECRET_KEY` | Flask secret key | `your-secret-key-here` |
| `FLASK_ENV` | Flask environment | `development` |
| `FLASK_DEBUG` | Flask debug mode | `True` |

### Jenkins Server Requirements

- Jenkins server must be running and accessible
- User must have appropriate permissions for:
  - Viewing jobs and builds
  - Triggering builds
  - Stopping builds
  - Viewing console output
  - Accessing node information
  - Viewing plugins

## API Endpoints

The application provides the following REST API endpoints:

### Jobs
- `GET /api/jobs` - Get all jobs
- `GET /api/job/<job_name>` - Get job details
- `POST /api/job/<job_name>/build` - Trigger build
- `POST /api/job/<job_name>/stop` - Stop running build
- `DELETE /api/job/<job_name>/delete` - Delete job
- `GET /api/job/<job_name>/builds` - Get build history

### Builds
- `GET /api/build/<job_name>/<build_number>` - Get build details
- `GET /api/build/<job_name>/<build_number>/console` - Get console output

### System
- `GET /api/nodes` - Get all nodes
- `GET /api/plugins` - Get installed plugins
- `GET /api/queue` - Get build queue
- `GET /api/statistics` - Get system statistics

## Usage

### Dashboard
The dashboard provides an overview of your Jenkins instance:
- **Statistics Cards**: Total jobs, nodes, queue size, and Jenkins version
- **Recent Jobs**: Quick access to the most recent jobs
- **Auto-refresh**: Statistics update automatically every 30 seconds

### Job Management
- **View Jobs**: Complete list of all Jenkins jobs
- **Build Jobs**: One-click build triggering
- **Stop Builds**: Stop running builds
- **Job Details**: Detailed information in modal view
- **Build History**: Complete build history with console access
- **Delete Jobs**: Remove jobs from Jenkins

### Build Monitoring
- **Real-time Status**: Color-coded build status indicators
- **Console Output**: Syntax-highlighted build logs
- **Build Parameters**: Support for parameterized builds
- **Build History**: Complete build timeline

### System Monitoring
- **Node Status**: Monitor build node health
- **Queue Status**: Real-time build queue monitoring
- **Plugin Management**: View installed plugins
- **System Statistics**: Overall system health

## Development

### Project Structure
```
jenkins-ui/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── env.example           # Environment configuration example
├── README.md             # This file
├── templates/
│   └── index.html        # Main HTML template
└── static/
    └── js/
        └── app.js        # Frontend JavaScript
```

### Adding New Features

1. **Backend (Flask)**
   - Add new routes in `app.py`
   - Implement Jenkins API calls
   - Add error handling

2. **Frontend (JavaScript)**
   - Add new functions in `static/js/app.js`
   - Update HTML template if needed
   - Add UI components

3. **Styling**
   - Modify CSS in `templates/index.html`
   - Use Bootstrap classes for consistency

### Testing

To test the application:

1. **Start Jenkins server** (if not already running)
2. **Configure environment** with correct Jenkins credentials
3. **Run the application**: `python app.py`
4. **Access the UI**: `http://localhost:5000`
5. **Test functionality**:
   - View dashboard
   - Browse jobs
   - Trigger builds
   - View build details
   - Check console output

## Troubleshooting

### Common Issues

1. **Connection Error**
   - Verify Jenkins URL is correct
   - Check Jenkins server is running
   - Verify credentials are correct

2. **Permission Errors**
   - Ensure user has appropriate Jenkins permissions
   - Check Jenkins security settings

3. **Build Failures**
   - Check Jenkins job configuration
   - Verify build parameters
   - Review console output for errors

4. **UI Issues**
   - Clear browser cache
   - Check browser console for JavaScript errors
   - Verify all static files are loading

### Debug Mode

Enable debug mode for development:
```bash
export FLASK_DEBUG=True
python app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Jenkins server logs
3. Check application logs
4. Create an issue in the repository

## Roadmap

Future enhancements:
- [ ] User authentication and authorization
- [ ] Job creation and configuration
- [ ] Pipeline visualization
- [ ] Advanced filtering and search
- [ ] Email notifications
- [ ] Mobile app
- [ ] Dark mode theme
- [ ] Multi-language support 