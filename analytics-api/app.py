from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger
from datetime import datetime
import os
from sqlalchemy import func, distinct, and_

app = Flask(__name__)

# PostgreSQL Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
swagger = Swagger(app)


# -------------------- Database Models --------------------
class Sites(db.Model):
    __tablename__ = "sites"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True)


class Hosts(db.Model):
    __tablename__ = "hosts"
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), index=True)
    name = db.Column(db.String, nullable=False, index=True)


class Projects(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    project_uuid = db.Column(db.String, nullable=False, index=True)
    project_name = db.Column(db.String, nullable=True, index=True)


class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    user_uuid = db.Column(db.String, nullable=False, index=True)
    user_email = db.Column(db.String, nullable=True, index=True)


class Slices(db.Model):
    __tablename__ = "slices"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    slice_guid = db.Column(db.String, nullable=False, index=True)
    slice_name = db.Column(db.String, nullable=False, index=True)
    state = db.Column(db.Integer, nullable=False, index=True)
    lease_start = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)
    lease_end = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)


class Slivers(db.Model):
    __tablename__ = "slivers"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), index=True)
    slice_id = db.Column(db.Integer, db.ForeignKey("slices.id"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    host_id = db.Column(db.Integer, db.ForeignKey("hosts.id"), index=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), index=True)
    sliver_guid = db.Column(db.String, nullable=False, index=True)
    state = db.Column(db.Integer, nullable=False, index=True)
    sliver_type = db.Column(db.String, nullable=False, index=True)
    ip_subnet = db.Column(db.String, nullable=True, index=True)
    image = db.Column(db.String, nullable=True)
    core = db.Column(db.Integer, nullable=True)
    ram = db.Column(db.Integer, nullable=True)
    disk = db.Column(db.Integer, nullable=True)
    bandwidth = db.Column(db.Integer, nullable=True)
    lease_start = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)
    lease_end = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)


class Components(db.Model):
    __tablename__ = "components"
    sliver_id = db.Column(db.Integer, db.ForeignKey("slivers.id"), primary_key=True)
    component_guid = db.Column(db.String, primary_key=True, index=True)
    type = db.Column(db.String, nullable=False, index=True)
    model = db.Column(db.String, nullable=False, index=True)
    bdfs = db.Column(db.JSON, nullable=True)  # Store BDFs as a JSON list


class Interfaces(db.Model):
    __tablename__ = "interfaces"
    sliver_id = db.Column(db.Integer, db.ForeignKey("slivers.id"), primary_key=True)
    interface_guid = db.Column(db.String, primary_key=True, index=True)
    port = db.Column(db.String, nullable=False, index=True)
    vlan = db.Column(db.String, nullable=True, index=True)
    bdf = db.Column(db.String, nullable=True, index=True)


# -------------------- API Routes --------------------

@app.route("/users", methods=["GET"])
def get_users():
    """
    Retrieve a list of users with their UUIDs.

    ---
    responses:
      200:
        description: "List of users"
    """
    users = db.session.query(Users.id, Users.user_uuid, Users.user_email).all()
    return jsonify([
        {
            "id": user.id,
            "user_uuid": user.user_uuid,
            "user_email": user.user_email,
        }
        for user in users
    ])


@app.route("/projects", methods=["GET"])
def get_projects():
    """
    Retrieve a list of projects with their UUIDs.

    ---
    responses:
      200:
        description: "List of projects"
    """
    projects = db.session.query(Projects.id, Projects.project_uuid, Projects.project_name).all()
    return jsonify([
        {
            "id": project.id,
            "project_uuid": project.project_uuid,
            "project_name": project.project_name,
        }
        for project in projects
    ])


@app.route("/slices", methods=["GET"])
def get_slices():
    """
    Retrieve slices with optional filters for time range, multiple states, project UUID, user UUID, component model, component type, and site.

    ---
    parameters:
      - name: start_time
        in: query
        type: string
        required: false
        description: "Filter slices that are active after this time. Format: YYYY-MM-DDTHH:MM:SS"
      - name: end_time
        in: query
        type: string
        required: false
        description: "Filter slices that are active before this time. Format: YYYY-MM-DDTHH:MM:SS"
      - name: state
        in: query
        type: string
        required: false
        description: "Filter slices by multiple states (comma-separated, e.g., '1,2,3')."
      - name: project_uuid
        in: query
        type: string
        required: false
        description: "Filter slices by project UUID."
      - name: user_uuid
        in: query
        type: string
        required: false
        description: "Filter slices by user UUID."
      - name: component_model
        in: query
        type: string
        required: false
        description: "Filter slices containing specific component models."
      - name: component_type
        in: query
        type: string
        required: false
        description: "Filter slices containing specific component types."
      - name: site_name
        in: query
        type: string
        required: false
        description: "Filter slices by site name."
      - name: page
        in: query
        type: integer
        required: false
        description: "Specify page number for pagination. Default is 1."
      - name: per_page
        in: query
        type: integer
        required: false
        description: "Number of records per page. Default is 10."
    responses:
      200:
        description: "Paginated list of filtered slices."
    """
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    state_param = request.args.get("state")
    project_uuid = request.args.get("project_uuid")
    user_uuid = request.args.get("user_uuid")
    component_model = request.args.get("component_model")
    component_type = request.args.get("component_type")
    site_name = request.args.get("site_name")
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    # Convert start_time and end_time to datetime objects
    try:
        if start_time:
            start_time = datetime.fromisoformat(start_time)
        if end_time:
            end_time = datetime.fromisoformat(end_time)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DDTHH:MM:SS"}), 400

    # Convert comma-separated states into a list of integers
    state_list = [int(s) for s in state_param.split(",")] if state_param else []

    # Base query ensuring a slice is counted only once per site
    query = (
        db.session.query(
            Slices.id,
            Slices.slice_guid,
            Slices.slice_name,
            Slices.state,
            Slices.lease_start,
            Slices.lease_end,
            Projects.project_uuid,
            Users.user_uuid,
            Sites.name.label("site_name"),
        )
        .join(Projects, Slices.project_id == Projects.id)
        .join(Users, Slices.user_id == Users.id)
        .outerjoin(Slivers, Slivers.slice_id == Slices.id)
        .outerjoin(Sites, Slivers.site_id == Sites.id)  # Join for site filtering
        .group_by(Slices.id, Slices.slice_guid, Slices.slice_name, Slices.state,
                  Slices.lease_start, Slices.lease_end, Projects.project_uuid,
                  Users.user_uuid, Sites.name)  # Ensures each slice is counted once per site
    )

    # Apply time range filters: Include slices that were active at any point in the given range
    if start_time and end_time:
        query = query.filter(
            (Slices.lease_start <= end_time) &  # Started before or within the range
            (Slices.lease_end >= start_time)  # Ended after or within the range
        )
    elif start_time:
        query = query.filter(Slices.lease_end >= start_time)  # Include slices that existed after start_time
    elif end_time:
        query = query.filter(Slices.lease_start <= end_time)  # Include slices that started before end_time

    # Apply multiple state filter using `IN`
    if state_list:
        query = query.filter(Slices.state.in_(state_list))

    # Filter by project UUID
    if project_uuid:
        query = query.filter(Projects.project_uuid == project_uuid)

    # Filter by user UUID
    if user_uuid:
        query = query.filter(Users.user_uuid == user_uuid)

    # Filter by component model
    if component_model:
        query = query.filter(Components.model == component_model)

    # Filter by component type
    if component_type:
        query = query.filter(Components.type == component_type)

    # Filter by site name
    if site_name:
        query = query.filter(Sites.name == site_name)

    # Apply pagination
    paginated_slices = query.distinct().paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "page": paginated_slices.page,
        "per_page": paginated_slices.per_page,
        "total_pages": paginated_slices.pages,
        "total_results": paginated_slices.total,
        "slices": [
            {
                "id": s.id,
                "guid": s.slice_guid,
                "name": s.slice_name,
                "state": s.state,
                "lease_start": s.lease_start.isoformat() if s.lease_start else None,
                "lease_end": s.lease_end.isoformat() if s.lease_end else None,
                "project_uuid": s.project_uuid,
                "user_uuid": s.user_uuid,
                "site_name": s.site_name,
            }
            for s in paginated_slices.items
        ]
    })


@app.route("/slivers", methods=["GET"])
def get_slivers():
    """
    Retrieve all slivers
    ---
    responses:
      200:
        description: List of slivers
    """
    slivers = Slivers.query.all()
    return jsonify([
        {"id": s.id, "guid": s.sliver_guid, "state": s.state, "type": s.sliver_type,
         "ip_subnet": s.ip_subnet, "lease_start": s.lease_start, "lease_end": s.lease_end}
        for s in slivers
    ])


@app.route("/components", methods=["GET"])
def get_components():
    """
    Retrieve all components
    ---
    responses:
      200:
        description: List of components
    """
    components = Components.query.all()
    return jsonify([
        {"guid": c.component_guid, "type": c.type, "model": c.model, "bdfs": c.bdfs}
        for c in components
    ])


@app.route("/interfaces", methods=["GET"])
def get_interfaces():
    """
    Retrieve all interfaces
    ---
    responses:
      200:
        description: List of interfaces
    """
    interfaces = Interfaces.query.all()
    return jsonify([
        {"guid": i.interface_guid, "port": i.port, "vlan": i.vlan, "bdf": i.bdf}
        for i in interfaces
    ])


@app.route("/slices_by_project", methods=["GET"])
def get_slices_by_project():
    """
    Get the number of slices created by a project within a time period.

    ---
    parameters:
      - name: project_uuid
        in: query
        type: string
        required: true
        description: "Filter by project UUID."
      - name: start_time
        in: query
        type: string
        required: false
        description: "Filter by start date (Format: YYYY-MM-DDTHH:MM:SS)."
      - name: end_time
        in: query
        type: string
        required: false
        description: "Filter by end date (Format: YYYY-MM-DDTHH:MM:SS)."
    responses:
      200:
        description: "Number of slices created by the project."
    """
    project_uuid = request.args.get("project_uuid")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")

    if not project_uuid:
        return jsonify({"error": "Project UUID is required"}), 400

    try:
        if start_time:
            start_time = datetime.fromisoformat(start_time)
        if end_time:
            end_time = datetime.fromisoformat(end_time)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    query = db.session.query(func.count(Slices.id)).join(Projects).filter(Projects.project_uuid == project_uuid)

    if start_time:
        query = query.filter(Slices.lease_start >= start_time)
    if end_time:
        query = query.filter(Slices.lease_end <= end_time)

    count = query.scalar()
    return jsonify({"project_uuid": project_uuid, "slices_created": count})


@app.route("/vms_by_project", methods=["GET"])
def get_vms_by_project():
    """
    Get the number of VMs created by a project.

    ---
    parameters:
      - name: project_uuid
        in: query
        type: string
        required: true
        description: "Filter by project UUID."
    responses:
      200:
        description: "Number of VMs created by the project."
    """
    project_uuid = request.args.get("project_uuid")

    if not project_uuid:
        return jsonify({"error": "Project UUID is required"}), 400

    count = db.session.query(func.count(Slivers.id)).join(Projects).filter(
        Projects.project_uuid == project_uuid
    ).scalar()

    return jsonify({"project_uuid": project_uuid, "vms_created": count})


@app.route("/vm_usage", methods=["GET"])
def get_vm_usage():
    """
    Get the aggregate number of VMs in use during a time period.

    ---
    parameters:
      - name: start_time
        in: query
        type: string
        required: true
        description: "Start date (Format: YYYY-MM-DDTHH:MM:SS)."
      - name: end_time
        in: query
        type: string
        required: true
        description: "End date (Format: YYYY-MM-DDTHH:MM:SS)."
    responses:
      200:
        description: "Number of VMs in use during the period."
    """
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")

    try:
        start_time = datetime.fromisoformat(start_time)
        end_time = datetime.fromisoformat(end_time)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    count = db.session.query(func.count(Slivers.id)).filter(
        Slivers.lease_start <= end_time,
        Slivers.lease_end >= start_time
    ).scalar()

    return jsonify({"vms_in_use": count})


@app.route("/resource_usage", methods=["GET"])
def get_resource_usage():
    """
    Retrieve resource usage based on component type, optionally filtered by time range, project UUID, and user UUID.
    """
    component_type = request.args.get("component_type")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    project_uuid = request.args.get("project_uuid")
    user_uuid = request.args.get("user_uuid")

    if not component_type:
        return jsonify({"error": "Component type is required"}), 400

    component_type = component_type.lower()

    # Convert time parameters to datetime objects
    try:
        if start_time:
            start_time = datetime.fromisoformat(start_time)
        if end_time:
            end_time = datetime.fromisoformat(end_time)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DDTHH:MM:SS"}), 400

    print(f"Query Params - Component: {component_type}, Start: {start_time}, End: {end_time}, Project: {project_uuid}, User: {user_uuid}")

    '''
    # Query resource usage with filters
    query = (
        db.session.query(
            Projects.project_uuid,
            Users.user_uuid,
            func.count(Components.component_guid).label("count")
        )
        .outerjoin(Slivers, Slivers.id == Components.sliver_id)
        .outerjoin(Slices, Slices.id == Slivers.slice_id)
        .outerjoin(Projects, Projects.id == Slivers.project_id)
        .outerjoin(Users, Users.id == Slivers.user_id)
        .filter(func.lower(Components.type) == component_type)
    )
    '''
    query = (
        db.session.query(
            Projects.project_uuid,
            Projects.project_name,
            Users.user_uuid,
            Users.user_email,
            func.count(Components.component_guid).label("count")
        )
            .outerjoin(Slivers, Slivers.id == Components.sliver_id)
            .outerjoin(Slices, Slices.id == Slivers.slice_id)  # Ensure the correct join path
            .outerjoin(Projects, Projects.id == Slices.project_id)  # Join Projects through Slices
            .outerjoin(Users, Users.id == Slices.user_id)  # Join Users through Slices
            .filter(func.lower(Components.type) == component_type.lower())  # Handle case-insensitivity
            .group_by(Projects.project_uuid, Projects.project_name, Users.user_uuid, Users.user_email)
    # Group by non-aggregated columns
    )

    # Apply time range filter: Components counted if slice was active within the range
    if start_time and end_time:
        query = query.filter(
            (Slices.lease_start <= end_time) &  # Started before or within the range
            (Slices.lease_end >= start_time)    # Ended after or within the range
        )
    elif start_time:
        query = query.filter(Slices.lease_end >= start_time)
    elif end_time:
        query = query.filter(Slices.lease_start <= end_time)

    # Apply project and user filters
    if project_uuid:
        query = query.filter(Projects.project_uuid == project_uuid)
    if user_uuid:
        query = query.filter(Users.user_uuid == user_uuid)

    # Group and order
    query = query.group_by(Projects.project_uuid, Users.user_uuid)
    query = query.order_by(func.count(Components.component_guid).desc())

    results = query.all()
    print(f"Results --- {results}")

    if not results:
        return jsonify({"message": "No data found"}), 200

    return jsonify([
        {
            "project_uuid": row.project_uuid,
            "project_name": row.project_name,
            "user_uuid": row.user_uuid,
            "user_email": row.user_email,
            "count": row.count
        } for row in results
    ])


@app.route("/user_slices", methods=["GET"])
def get_user_slices():
    """
    Get the number of slices created by a user.

    ---
    parameters:
      - name: user_uuid
        in: query
        type: string
        required: true
        description: "User UUID."
    responses:
      200:
        description: "Number of slices created by the user."
    """
    user_uuid = request.args.get("user_uuid")

    if not user_uuid:
        return jsonify({"error": "User UUID is required"}), 400

    count = db.session.query(func.count(Slices.id)).join(Users).filter(
        Users.user_uuid == user_uuid
    ).scalar()

    return jsonify({"user_uuid": user_uuid, "slices_created": count})


@app.route("/active_slices_per_rack", methods=["GET"])
def get_active_slices_per_rack():
    """
    Get the number of active slices per rack.

    ---
    responses:
      200:
        description: "Active slices per rack."
    """
    query = (
        db.session.query(Sites.name, func.count(Slices.id).label("active_slices"))
        .join(Slivers, Slivers.site_id == Sites.id)
        .join(Slices, Slices.id == Slivers.slice_id)
        .filter(Slices.state == 1)  # Active slices
        .group_by(Sites.name)
    )

    results = [{"site": site, "active_slices": count} for site, count in query]
    return jsonify(results)


@app.route("/active_users", methods=["GET"])
def get_active_users():
    """
    Get the number of active users in a time period.

    ---
    parameters:
      - name: start_time
        in: query
        type: string
        required: true
        description: "Start date (Format: YYYY-MM-DDTHH:MM:SS)."
      - name: end_time
        in: query
        type: string
        required: true
        description: "End date (Format: YYYY-MM-DDTHH:MM:SS)."
    responses:
      200:
        description: "Number of active users in the given time period."
    """
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")

    try:
        start_time = datetime.fromisoformat(start_time)
        end_time = datetime.fromisoformat(end_time)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    count = db.session.query(func.count(distinct(Slices.user_id))).filter(
        and_(Slices.lease_start <= end_time, Slices.lease_end >= start_time)
    ).scalar()

    return jsonify({"active_users": count})


@app.route("/slice_failures", methods=["GET"])
def get_slice_failures():
    """
    Get slice failure counts by error type.

    ---
    responses:
      200:
        description: "Slice failure counts."
    """
    query = (
        db.session.query(Slices.state, func.count(Slices.id).label("failure_count"))
        .filter(Slices.state >= 400)  # Failure states
        .group_by(Slices.state)
    )

    results = [{"error_type": state, "failure_count": count} for state, count in query]
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

