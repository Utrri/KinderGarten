import requests
from config import API_BASE_URL


class KindergartenDB:
    def __init__(self):
        self.base_url = API_BASE_URL

    def _get(self, path, params=None):
        response = requests.get(f"{self.base_url}{path}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def _post(self, path, data=None):
        response = requests.post(f"{self.base_url}{path}", json=data or {}, timeout=10)
        response.raise_for_status()
        return response.json()

    def login_user(self, username, password):
        return self._post("/login", {
            "username": username,
            "password": password
        }).get("user")

    def register_user(self, username, password, user_type, full_name, child_name=None, group_name=None,
                      parent_phone=None, child_birthdate=None):
        return self._post("/register", {
            "username": username,
            "password": password,
            "user_type": user_type,
            "full_name": full_name,
            "child_name": child_name,
            "group_name": group_name,
            "parent_phone": parent_phone,
            "child_birthdate": child_birthdate
        }).get("success", False)

    def get_services(self):
        return self._get("/services").get("items", [])

    def get_all_teachers(self):
        return self._get("/all-teachers").get("items", [])

    def get_all_users_grouped(self):
        return self._get("/all-users-grouped").get("items", [])

    def get_children_by_parent(self, parent_name):
        return self._get("/children-by-parent", {"parent_name": parent_name}).get("items", [])

    def get_children_by_group(self, group_name):
        return self._get("/children-by-group", {"group_name": group_name}).get("items", [])

    def update_children_groups_by_age(self):
        return self._post("/update-children-groups")

    def get_child_full_info(self, child_name):
        return self._get("/child-full-info", {
            "child_name": child_name
        }).get("item")

    def get_child_service_ids(self, child_name):
        return self._get("/child-service-ids", {"child_name": child_name}).get("items", [])

    def get_child_services(self, child_name):
        return self._get("/child-services", {"child_name": child_name}).get("items", [])

    def get_attendance(self, child_name=None, group_name=None, date=None):
        return self._get("/attendance", {
            "child_name": child_name,
            "group_name": group_name,
            "date": date
        }).get("items", [])

    def get_attendance_for_child_service_month(self, child_name, service_id, first_day, last_day):
        return self._get("/attendance-month", {
            "child_name": child_name,
            "service_id": service_id,
            "first_day": first_day,
            "last_day": last_day
        }).get("items", [])

    def get_services_by_teacher(self, teacher_name):
        return self._get("/services-by-teacher", {"teacher_name": teacher_name}).get("items", [])

    def get_services_by_teacher_full(self, teacher_name):
        return self._get("/services-by-teacher-full", {"teacher_name": teacher_name}).get("items", [])

    def get_enrolled_children_by_service(self, service_id):
        return self._get("/enrolled-children-by-service", {"service_id": service_id}).get("items", [])

    def get_enrolled_children_by_teacher(self, teacher_name):
        return self._get("/enrolled-children-by-teacher", {"teacher_name": teacher_name}).get("items", [])

    def is_service_in_group(self, service_id, group_name):
        return self._get("/is-service-in-group", {
            "service_id": service_id,
            "group_name": group_name
        }).get("success", False)

    def get_unique_groups(self):
        return self._get("/unique-groups").get("items", [])

    def get_min_parent_user_id(self, full_name):
        return self._get("/min-parent-user-id", {"full_name": full_name}).get("value")

    def enroll_child_to_service(self, child_name, service_id):
        return self._post("/service-enrollments", {
            "child_name": child_name,
            "service_id": int(service_id)
        }).get("success", False)

    def unenroll_child_from_service(self, child_name, service_id):
        return self._post("/delete-service-enrollment", {
            "child_name": child_name,
            "service_id": int(service_id)
        }).get("success", False)


    def mark_attendance(self, child_name, service_id, date, status, reason, group_name):
        return self._post("/mark-attendance", {
            "child_name": child_name,
            "service_id": int(service_id),
            "date": date,
            "status": status,
            "reason": reason,
            "group_name": group_name
        }).get("success", False)

    def delete_attendance(self, child_name, service_id, date_str):
        return self._post("/delete-attendance", {
            "child_name": child_name,
            "service_id": int(service_id),
            "date": date_str
        }).get("success", False)

    def add_service(self, name, description, price, teacher_name):
        return self._post("/add-service", {
            "name": name,
            "description": description,
            "price": float(price),
            "teacher_name": teacher_name
        }).get("success", False)

    def update_service_full(self, service_id, name, description, price, teacher_name):
        return self._post("/update-service", {
            "service_id": int(service_id),
            "name": name,
            "description": description,
            "price": float(price),
            "teacher_name": teacher_name
        }).get("success", False)

    def delete_service(self, service_id):
        return self._post("/delete-service", {
            "service_id": int(service_id)
        }).get("success", False)

    def update_user_full(self, user_id, username, password, user_type, full_name, child_name, group_name):
        return self._post("/update-user", {
            "user_id": int(user_id),
            "username": username,
            "password": password,
            "user_type": user_type,
            "full_name": full_name,
            "child_name": child_name,
            "group_name": group_name
        }).get("success", False)

    def add_child_to_parent(self, parent_name, child_name, parent_phone=None, child_birthdate=None):
        return self._post("/add-child", {
            "parent_name": parent_name,
            "child_name": child_name,
            "parent_phone": parent_phone,
            "child_birthdate": child_birthdate
        }).get("success", False)

    def update_child(self, parent_name, old_child_name, new_child_name, parent_phone=None, child_birthdate=None):
        return self._post("/update-child", {
            "parent_name": parent_name,
            "old_child_name": old_child_name,
            "new_child_name": new_child_name,
            "parent_phone": parent_phone,
            "child_birthdate": child_birthdate
        }).get("success", False)

    def delete_child(self, parent_name, child_name):
        return self._post("/delete-child", {
            "parent_name": parent_name,
            "child_name": child_name
        }).get("success", False)

    def delete_user(self, user_id):
        return self._post("/delete-user", {
            "user_id": int(user_id)
        }).get("success", False)

    def mark_all_children_for_service_date(self, service_id, date_str, status):
        return self._post("/bulk-mark-service-date", {
            "service_id": int(service_id),
            "date": date_str,
            "status": status
        })

    def reset_all_children_for_service_date(self, service_id, date_str):
        return self._post("/bulk-reset-service-date", {
            "service_id": int(service_id),
            "date": date_str
        })

    def get_attendance_report_data(self, start_date, end_date, group_filter):
        return self._get("/report-attendance", {
            "start_date": start_date,
            "end_date": end_date,
            "group_filter": group_filter
        }).get("items", [])

    def get_payment_report_data(self, start_date, end_date, group_filter):
        return self._get("/report-payment", {
            "start_date": start_date,
            "end_date": end_date,
            "group_filter": group_filter
        }).get("items", [])

    def get_users_report_data(self):
        return self._get("/report-users").get("items", [])

    def get_services_report_data(self):
        return self._get("/report-services").get("items", [])