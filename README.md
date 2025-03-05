# sliver-analytics
## Overview
The Sliver Analytics Dashboard is a web-based tool for tracking and analyzing sliver allocations across projects and users. It provides insights into resource usage with time-based, user-based, and project-based filtering.

The system consists of multiple services, including a PostgreSQL database, an API layer, a Dash-based visualization app, and Nginx for reverse proxying.

### Features
- Filter slivers by component type (SharedNIC, SmartNIC, FPGA, GPU, NVMe, Storage).
- Time-based filtering to analyze sliver allocations over specific periods.
- Identify the project or user with the most allocated slivers.
- Secure authentication with Vouch Proxy integration.
- Scalable microservices architecture using Docker.

## Architecture
The system is composed of the following Docker containers:

### Service	Description
- database: PostgreSQL database storing sliver data.
- nginx: Nginx reverse proxy handling HTTPS traffic.
- analytics-api: Backend API serving sliver-related data.
- dash-app: Dash-based web application for visualization.
- vouch-proxy: Authentication proxy for securing API requests.

### Network Segmentation
- frontend network: Exposes services to the external world (e.g., Nginx, Dash app).
- backend network: Internal network for database and API communication.

## Setup & Installation
### Prerequisites
- Docker & Docker Compose installed on your system.
- SSL certificates for secure API communication (optional).

### 1. Clone the Repository
```
git clone https://github.com/yourusername/sliver-analytics.git
cd sliver-analytics
```


### 2. Configure Environment Variables
Create a .env file to specify database and service settings:

```
POSTGRES_HOST=database
POSTGRES_DB=analytics
POSTGRES_USER=fabric
POSTGRES_PASSWORD=fabric
PGDATA=/var/lib/postgresql/data
API_URL=http://analytics-api:5000
```

### 3. Build & Run the Services
```
docker-compose up --build -d
--build ensures any changes in the application are incorporated.
-d runs services in detached mode.
```

## Usage
Accessing the Dashboard
Once the containers are running, open your browser and navigate to: https://localhost:8443

Ensure you have the proper SSL certificates configured in the `./ssl/` directory.

### API Endpoints
The backend API provides endpoints for fetching sliver-related data:

```
GET /slivers_by_component?component_type=GPU&start_date=2024-01-01&end_date=2024-01-31
GET /project_with_most_slivers?component_type=SmartNIC
GET /user_with_most_slivers?component_type=FPGA
```

### Security & Authentication
- Vouch Proxy ensures API requests are authenticated.
- HTTPS is enforced using Nginx with SSL certificates.

## Troubleshooting
- Check Logs
- To view logs for a specific container, use:
```
docker logs -f analytics-api
```
- Restart a Service
If a service fails, restart it with:
```
docker-compose restart dash-app
```
- Remove & Rebuild Everything
```
docker-compose down -v
docker-compose up --build -d
```

## Future Enhancements
- Role-based access control (RBAC) for API endpoints.
- Advanced filtering (e.g., resource utilization trends, forecasting).

## Contributing
Feel free to fork this repository and submit pull requests.

## License
This project is licensed under the MIT License.
