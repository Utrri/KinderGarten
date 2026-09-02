from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from server_db import KindergartenDB

app = FastAPI()
db = KindergartenDB()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    user_type: str
    full_name: str
    child_name: Optional[str] = None
    group_name: Optional[str] = None
    parent_phone: Optional[str] = None
    child_birthdate: Optional[str] = None

class EnrollRequest(BaseModel):
    child_name: str
    service_id: int

class UnenrollRequest(BaseModel):
    child_name: str
    service_id: int

class AttendanceRequest(BaseModel):
    child_name: str
    service_id: int
    date: str
    status: str
    reason: str = ""
    group_name: str


class DeleteAttendanceRequest(BaseModel):
    child_name: str
    service_id: int
    date: str


class AddServiceRequest(BaseModel):
    name: str
    description: str
    price: float
    teacher_name: str


class UpdateServiceRequest(BaseModel):
    service_id: int
    name: str
    description: str
    price: float
    teacher_name: str


class DeleteServiceRequest(BaseModel):
    service_id: int


class UpdateUserRequest(BaseModel):
    user_id: int
    username: str
    password: str
    user_type: str
    full_name: str
    child_name: Optional[str] = None
    group_name: Optional[str] = None


class AddChildRequest(BaseModel):
    parent_name: str
    child_name: str
    parent_phone: Optional[str] = None
    child_birthdate: str


class UpdateChildRequest(BaseModel):
    parent_name: str
    old_child_name: str
    new_child_name: str
    parent_phone: Optional[str] = None
    child_birthdate: Optional[str] = None


class DeleteChildRequest(BaseModel):
    parent_name: str
    child_name: str


class DeleteUserRequest(BaseModel):
    user_id: int


class BulkMarkRequest(BaseModel):
    service_id: int
    date: str
    status: str


class BulkResetRequest(BaseModel):
    service_id: int
    date: str


@app.post("/login")
def login(data: LoginRequest):
    user = db.login_user(data.username, data.password)
    return {"user": user}


@app.post("/register")
def register(data: RegisterRequest):
    success = db.register_user(
        data.username,
        data.password,
        data.user_type,
        data.full_name,
        data.child_name,
        data.group_name,
        data.parent_phone,
        data.child_birthdate
    )
    return {"success": success}


@app.get("/services")
def get_services():
    return {"items": db.get_services()}


@app.get("/all-teachers")
def get_all_teachers():
    return {"items": db.get_all_teachers()}


@app.get("/all-users-grouped")
def get_all_users_grouped():
    return {"items": db.get_all_users_grouped()}


@app.get("/children-by-parent")
def get_children_by_parent(parent_name: str):
    return {"items": db.get_children_by_parent(parent_name)}


@app.get("/children-by-group")
def get_children_by_group(group_name: str):
    return {"items": db.get_children_by_group(group_name)}

@app.get("/child-full-info")
def get_child_full_info(child_name: str):
    return {"item": db.get_child_full_info(child_name)}


@app.get("/child-service-ids")
def get_child_service_ids(child_name: str):
    return {"items": db.get_child_service_ids(child_name)}


@app.get("/child-services")
def get_child_services(child_name: str):
    return {"items": db.get_child_services(child_name)}


@app.get("/attendance")
def get_attendance(
    child_name: Optional[str] = None,
    group_name: Optional[str] = None,
    date: Optional[str] = None
):
    return {"items": db.get_attendance(child_name=child_name, group_name=group_name, date=date)}


@app.get("/attendance-month")
def get_attendance_month(child_name: str, service_id: int, first_day: str, last_day: str):
    with db.conn.cursor() as cursor:
        cursor.execute("""
            SELECT date, status
            FROM attendance
            WHERE child_name = %s AND service_id = %s
              AND date BETWEEN %s AND %s
            ORDER BY date
        """, (child_name, service_id, first_day, last_day))
        rows = cursor.fetchall()
    return {"items": rows}


@app.get("/services-by-teacher")
def get_services_by_teacher(teacher_name: str):
    return {"items": db.get_services_by_teacher(teacher_name)}


@app.get("/services-by-teacher-full")
def get_services_by_teacher_full(teacher_name: str):
    return {"items": db.get_services_by_teacher_full(teacher_name)}


@app.get("/enrolled-children-by-service")
def get_enrolled_children_by_service(service_id: int):
    return {"items": db.get_enrolled_children_by_service(service_id)}


@app.get("/enrolled-children-by-teacher")
def get_enrolled_children_by_teacher(teacher_name: str):
    return {"items": db.get_enrolled_children_by_teacher(teacher_name)}


@app.get("/is-service-in-group")
def is_service_in_group(service_id: int, group_name: str):
    return {"success": db.is_service_in_group(service_id, group_name)}


@app.get("/unique-groups")
def get_unique_groups():
    with db.conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT group_name
            FROM users
            WHERE group_name IS NOT NULL
            ORDER BY group_name
        """)
        rows = [r[0] for r in cursor.fetchall()]
    return {"items": rows}


@app.post("/update-children-groups")
def update_children_groups():
    return db.update_all_children_groups_by_age()


@app.get("/min-parent-user-id")
def get_min_parent_user_id(full_name: str):
    with db.conn.cursor() as cursor:
        cursor.execute(
            "SELECT MIN(id) FROM users WHERE full_name = %s AND user_type = 'parent'",
            (full_name,)
        )
        row = cursor.fetchone()
    return {"value": row[0] if row and row[0] else None}


@app.post("/service-enrollments")
def enroll_child(data: EnrollRequest):
    return {"success": db.enroll_child_to_service(data.child_name, data.service_id)}

@app.post("/delete-service-enrollment")
def delete_service_enrollment(data: UnenrollRequest):
    return {
        "success": db.unenroll_child_from_service(
            data.child_name,
            data.service_id
        )
    }

@app.post("/mark-attendance")
def mark_attendance(data: AttendanceRequest):
    success = db.mark_attendance(
        data.child_name,
        data.service_id,
        data.date,
        data.status,
        data.reason,
        data.group_name
    )
    return {"success": success}


@app.post("/delete-attendance")
def delete_attendance(data: DeleteAttendanceRequest):
    success = db.delete_attendance(data.child_name, data.service_id, data.date)
    return {"success": success}


@app.post("/add-service")
def add_service(data: AddServiceRequest):
    return {"success": db.add_service(data.name, data.description, data.price, data.teacher_name)}


@app.post("/update-service")
def update_service(data: UpdateServiceRequest):
    return {
        "success": db.update_service_full(
            data.service_id,
            data.name,
            data.description,
            data.price,
            data.teacher_name
        )
    }


@app.post("/delete-service")
def delete_service(data: DeleteServiceRequest):
    return {"success": db.delete_service(data.service_id)}


@app.post("/update-user")
def update_user(data: UpdateUserRequest):
    return {
        "success": db.update_user_full(
            data.user_id,
            data.username,
            data.password,
            data.user_type,
            data.full_name,
            data.child_name,
            data.group_name
        )
    }


@app.post("/add-child")
def add_child(data: AddChildRequest):
    return {
        "success": db.add_child_to_parent(
            data.parent_name,
            data.child_name,
            data.parent_phone,
            data.child_birthdate
        )
    }


@app.post("/update-child")
def update_child(data: UpdateChildRequest):
    return {
        "success": db.update_child(
            data.parent_name,
            data.old_child_name,
            data.new_child_name,
            data.child_birthdate,
            data.parent_phone
        )
    }


@app.post("/delete-child")
def delete_child(data: DeleteChildRequest):
    return {"success": db.delete_child(data.parent_name, data.child_name)}


@app.post("/delete-user")
def delete_user(data: DeleteUserRequest):
    return {"success": db.delete_user(data.user_id)}


@app.post("/bulk-mark-service-date")
def bulk_mark_service_date(data: BulkMarkRequest):
    count = 0
    with db.conn.cursor() as cursor:
        children = db.get_enrolled_children_by_service(data.service_id)

        for child in children:
            cursor.execute("""
                SELECT id FROM attendance
                WHERE child_name = %s AND service_id = %s AND date = %s
            """, (child, data.service_id, data.date))
            exists = cursor.fetchone()

            if not exists:
                cursor.execute("""
                    SELECT group_name
                    FROM users
                    WHERE child_name = %s AND user_type = 'parent'
                    LIMIT 1
                """, (child,))
                group_row = cursor.fetchone()
                group_name = group_row[0] if group_row else "Неизвестно"

                ok = db.mark_attendance(
                    child,
                    data.service_id,
                    data.date,
                    data.status,
                    "",
                    group_name
                )
                if ok:
                    count += 1

    return {"success": True, "count": count}


@app.post("/bulk-reset-service-date")
def bulk_reset_service_date(data: BulkResetRequest):
    count = 0
    children = db.get_enrolled_children_by_service(data.service_id)

    for child in children:
        ok = db.delete_attendance(child, data.service_id, data.date)
        if ok:
            count += 1

    return {"success": True, "count": count}


@app.get("/report-attendance")
def report_attendance(start_date: str, end_date: str, group_filter: str):
    with db.conn.cursor() as cursor:
        query = """
            SELECT
                a.child_name,
                u.group_name,
                s.name,
                a.date,
                a.status,
                s.price
            FROM attendance a
            JOIN users u
                ON a.child_name = u.child_name
               AND u.user_type = 'parent'
            JOIN services s
                ON a.service_id = s.id
            WHERE a.date BETWEEN %s AND %s
        """

        params = [start_date, end_date]

        if group_filter != "Все группы":
            query += " AND u.group_name = %s"
            params.append(group_filter)

        query += """
            ORDER BY
                a.date,
                a.child_name,
                s.name
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()

    return {"items": rows}


@app.get("/report-payment")
def report_payment(start_date: str, end_date: str, group_filter: str):
    with db.conn.cursor() as cursor:
        query = """
            SELECT
                u.full_name,
                a.child_name,
                u.group_name,
                s.name,
                COUNT(*) FILTER (WHERE a.status = 'присутствовал') AS visits_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN a.status = 'присутствовал' THEN s.price
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_sum
            FROM attendance a
            JOIN users u
                ON a.child_name = u.child_name
               AND u.user_type = 'parent'
            JOIN services s
                ON a.service_id = s.id
            WHERE a.date BETWEEN %s AND %s
        """

        params = [start_date, end_date]

        if group_filter != "Все группы":
            query += " AND u.group_name = %s"
            params.append(group_filter)

        query += """
            GROUP BY
                u.full_name,
                a.child_name,
                u.group_name,
                s.id,
                s.name
            ORDER BY
                u.full_name,
                a.child_name,
                s.name
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()

    return {"items": rows}


@app.get("/report-users")
def report_users():
    with db.conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT full_name, MIN(username)
            FROM users
            WHERE user_type = 'parent' AND username != 'admin'
            GROUP BY full_name
            ORDER BY full_name
        """)
        parents = cursor.fetchall()

        result = []

        for parent_name, main_username in parents:
            cursor.execute("""
                SELECT child_name, group_name
                FROM users
                WHERE full_name = %s AND user_type = 'parent' AND child_name IS NOT NULL
                ORDER BY child_name
            """, (parent_name,))
            children = cursor.fetchall()

            result.append([main_username, "Родитель", parent_name, "", children[0][1] if children else ""])

            for child_name, group_name in children:
                result.append(["", "", "", child_name, group_name or ""])

        cursor.execute("""
            SELECT username, full_name, group_name
            FROM users
            WHERE user_type = 'teacher' AND username != 'admin'
            ORDER BY full_name
        """)
        teachers = cursor.fetchall()

        for username, full_name, group_name in teachers:
            result.append([username, "Воспитатель", full_name, "", group_name or ""])

    return {"items": result}


@app.get("/report-services")
def report_services():
    with db.conn.cursor() as cursor:
        cursor.execute("""
            SELECT name, description, price, teacher_name
            FROM services
            ORDER BY name
        """)
        rows = cursor.fetchall()
    return {"items": rows}