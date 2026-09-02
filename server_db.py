import psycopg
import hashlib
import traceback
from datetime import date, datetime

class KindergartenDB:
    def __init__(self):
        try:
            print("Подключение к PostgreSQL...")
            self.conn = psycopg.connect(
                host="127.0.0.1",
                port=5432,
                dbname="postgres",
                user="postgres",
                password="10102006",
                connect_timeout=5
            )
            self.conn.autocommit = False
            print("PostgreSQL подключена")

            print("Создание таблиц...")
            self.create_tables()
            print("Таблицы готовы")

            print("Добавление тестовых данных...")
            self.add_sample_data()
            print("Тестовые данные готовы")

            print("Обновление групп детей по возрасту...")
            self.update_all_children_groups_by_age()
            print("Группы детей обновлены")

        except Exception as e:
            print(f"Ошибка подключения к БД: {e}")
            print(traceback.format_exc())
            raise

    def is_admin(self, username):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                return user and user[0] == "admin"
        except Exception:
            return False

    def calculate_age_months(self, birthdate):
        """
        Возвращает возраст ребенка в месяцах.
        """
        try:
            if isinstance(birthdate, str):
                birthdate = datetime.strptime(birthdate, "%Y-%m-%d").date()

            today = date.today()

            months = (today.year - birthdate.year) * 12 + (today.month - birthdate.month)

            if today.day < birthdate.day:
                months -= 1

            return months

        except Exception:
            return None

    def get_child_group_by_birthdate(self, birthdate):
        """
        Определяет группу ребенка по дате рождения.
        """
        age_months = self.calculate_age_months(birthdate)

        if age_months is None:
            return None, None

        if age_months < 17:
            return None, "Возраст ребенка должен быть не меньше 1 года 5 месяцев"

        if age_months > 96:
            return None, "Возраст ребенка не должен превышать 8 лет"

        if 17 <= age_months < 36:
            return "Непоседы", "первая младшая группа"

        if 36 <= age_months < 48:
            return "Буратино", "младшая группа"

        if 48 <= age_months < 60:
            return "Затейники", "средняя группа"

        if 60 <= age_months < 72:
            return "Фантазёры", "старшая группа"

        if 72 <= age_months <= 96:
            return "Улыбка", "подготовительная группа"

        return None, "Возраст ребенка не подходит для ДОУ"

    def update_all_children_groups_by_age(self):
        """
        Автоматически обновляет группы детей на основе даты рождения.
        """
        try:
            updated_count = 0
            skipped_count = 0

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, child_birthdate
                    FROM users
                    WHERE user_type = 'parent'
                      AND child_name IS NOT NULL
                      AND child_birthdate IS NOT NULL
                """)

                children = cursor.fetchall()

                for child_id, child_birthdate in children:
                    group_name, group_type = self.get_child_group_by_birthdate(child_birthdate)

                    if group_name:
                        cursor.execute("""
                            UPDATE users
                            SET group_name = %s
                            WHERE id = %s
                        """, (group_name, child_id))
                        updated_count += 1
                    else:
                        skipped_count += 1

                self.conn.commit()

            return {
                "success": True,
                "updated": updated_count,
                "skipped": skipped_count
            }

        except Exception as e:
            print(f"Ошибка при обновлении групп детей: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return {
                "success": False,
                "updated": 0,
                "skipped": 0
            }

    def format_child_age(self, birthdate):
        age_months = self.calculate_age_months(birthdate)

        if age_months is None:
            return ""

        years = age_months // 12
        months = age_months % 12

        def year_word(n):
            if n % 10 == 1 and n % 100 != 11:
                return "год"
            if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
                return "года"
            return "лет"

        def month_word(n):
            if n % 10 == 1 and n % 100 != 11:
                return "месяц"
            if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
                return "месяца"
            return "месяцев"

        parts = []

        if years > 0:
            parts.append(f"{years} {year_word(years)}")

        if months > 0:
            parts.append(f"{months} {month_word(months)}")

        if not parts:
            return "0 месяцев"

        return " ".join(parts)


    def update_service_description(self, service_id, new_description):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE services SET description = %s WHERE id = %s",
                    (new_description, service_id)
                )
                self.conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка при обновлении описания услуги ID {service_id}: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def update_user_full(self, user_id, username, password, user_type, full_name, child_name, group_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET username=%s, password=%s, user_type=%s, full_name=%s, child_name=%s, group_name=%s
                    WHERE id=%s
                """, (username, password, user_type, full_name, child_name, group_name, user_id))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при update_user_full: {e}")
            self.conn.rollback()
            return False

    def delete_service(self, service_id):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT * FROM services WHERE id = %s", (service_id,))
                service = cursor.fetchone()
                if not service:
                    return False

                cursor.execute("DELETE FROM service_enrollments WHERE service_id = %s", (service_id,))
                cursor.execute("DELETE FROM attendance WHERE service_id = %s", (service_id,))
                cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления услуги: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def delete_user(self, user_id):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, password, user_type, full_name, child_name, group_name
                    FROM users
                    WHERE id = %s
                """, (user_id,))
                user = cursor.fetchone()

                if not user:
                    return False

                user_id, username, password, user_type, full_name, child_name, group_name = user

                if user_type == 'parent':
                    cursor.execute(
                        "SELECT id FROM users WHERE full_name = %s AND user_type = 'parent'",
                        (full_name,)
                    )
                    all_children = cursor.fetchall()

                    for child_id_row in all_children:
                        child_id_value = child_id_row[0]

                        cursor.execute("SELECT child_name FROM users WHERE id = %s", (child_id_value,))
                        child_name_result = cursor.fetchone()

                        if child_name_result:
                            child_name_to_delete = child_name_result[0]
                            cursor.execute("DELETE FROM attendance WHERE child_name = %s", (child_name_to_delete,))
                            cursor.execute("DELETE FROM service_enrollments WHERE child_name = %s", (child_name_to_delete,))

                        cursor.execute("DELETE FROM users WHERE id = %s", (child_id_value,))
                else:
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления пользователя: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def create_tables(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        user_type TEXT NOT NULL,
                        full_name TEXT NOT NULL,
                        child_name TEXT,
                        group_name TEXT
                    )
                """)

                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS parent_phone TEXT")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS child_birthdate DATE")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS services (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        price NUMERIC(10,2) NOT NULL,
                        teacher_name TEXT
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attendance (
                        id SERIAL PRIMARY KEY,
                        child_name TEXT NOT NULL,
                        service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
                        date TEXT NOT NULL,
                        status TEXT NOT NULL,
                        reason TEXT,
                        group_name TEXT NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS service_enrollments (
                        id SERIAL PRIMARY KEY,
                        child_name TEXT NOT NULL,
                        service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE
                    )
                """)

                self.conn.commit()
        except Exception as e:
            print(f"Ошибка создания таблиц: {e}")
            print(traceback.format_exc())
            self.conn.rollback()

    def login_user(self, username, password):
        try:
            if not username or not password:
                return None
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s AND password = %s",
                    (username, hashed_password)
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"Ошибка входа: {e}")
            return None

    def register_user(self, username, password, user_type, full_name, child_name=None, group_name=None,
                      parent_phone=None, child_birthdate=None):
        try:
            if not username or not password or not user_type or not full_name:
                return False

            if user_type == "teacher" and not group_name:
                return False

            if user_type == "parent":
                if not child_name or not child_birthdate or not parent_phone:
                    return False

                group_name, group_type = self.get_child_group_by_birthdate(child_birthdate)

                if not group_name:
                    print(group_type)
                    return False

            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (
                        username, password, user_type, full_name, child_name, group_name, parent_phone, child_birthdate
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    username,
                    hashed_password,
                    user_type,
                    full_name,
                    child_name,
                    group_name,
                    parent_phone,
                    child_birthdate
                ))

                self.conn.commit()
                return True

        except psycopg.errors.UniqueViolation:
            self.conn.rollback()
            return False
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def get_unique_parents(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        MIN(id) as main_id,
                        full_name,
                        MIN(username) as main_username,
                        'parent' as user_type,
                        STRING_AGG(DISTINCT group_name, ',') as groups
                    FROM users
                    WHERE user_type = 'parent' AND username != 'admin'
                    GROUP BY full_name
                    ORDER BY full_name
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения уникальных родителей: {e}")
            return []

    def get_all_users_grouped(self):
        try:
            result = []

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        MIN(id) as main_id,
                        full_name,
                        MIN(username) as main_username,
                        MIN(password) as main_password,
                        'parent' as user_type,
                        STRING_AGG(DISTINCT group_name, ',') as groups,
                        STRING_AGG(DISTINCT child_name, ',') as children,
                        MAX(parent_phone) as parent_phone,
                        MIN(child_birthdate) as first_child_birthdate
                    FROM users
                    WHERE user_type = 'parent' AND username != 'admin'
                    GROUP BY full_name
                    ORDER BY full_name
                """)
                parents = cursor.fetchall()

                for parent in parents:
                    (
                        main_id,
                        full_name,
                        main_username,
                        main_password,
                        user_type,
                        groups,
                        children,
                        parent_phone,
                        first_child_birthdate
                    ) = parent

                    children_list = children.split(',') if children else []
                    groups_list = groups.split(',') if groups else []

                    result.append([
                        main_id,
                        main_username,
                        main_password,
                        user_type,
                        full_name,
                        children_list[0] if children_list else "",
                        groups_list[0] if groups_list else "",
                        parent_phone or "",
                        str(first_child_birthdate) if first_child_birthdate else ""
                    ])

                cursor.execute("""
                    SELECT
                        id,
                        username,
                        password,
                        user_type,
                        full_name,
                        child_name,
                        group_name,
                        parent_phone,
                        child_birthdate
                    FROM users
                    WHERE user_type = 'teacher' AND username != 'admin'
                    ORDER BY full_name
                """)
                teachers = cursor.fetchall()

                for teacher in teachers:
                    result.append([
                        teacher[0],
                        teacher[1],
                        teacher[2],
                        teacher[3],
                        teacher[4],
                        teacher[5],
                        teacher[6],
                        teacher[7] or "",
                        str(teacher[8]) if teacher[8] else ""
                    ])

                cursor.execute("""
                    SELECT
                        id,
                        username,
                        password,
                        user_type,
                        full_name,
                        child_name,
                        group_name,
                        parent_phone,
                        child_birthdate
                    FROM users
                    WHERE username = 'admin'
                """)
                admin = cursor.fetchone()

                if admin:
                    result.append([
                        admin[0],
                        admin[1],
                        admin[2],
                        admin[3],
                        admin[4],
                        admin[5],
                        admin[6],
                        admin[7] or "",
                        str(admin[8]) if admin[8] else ""
                    ])

            return result

        except Exception as e:
            print(f"Ошибка получения сгруппированных пользователей: {e}")
            print(traceback.format_exc())
            return []

    def get_all_users(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users ORDER BY user_type, full_name")
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения пользователей: {e}")
            return []

    def get_services(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT * FROM services ORDER BY id")
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения услуг: {e}")
            return []

    def add_service(self, name, description, price, teacher_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO services (name, description, price, teacher_name)
                    VALUES (%s, %s, %s, %s)
                """, (name, description, price, teacher_name))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка добавления услуги: {e}")
            self.conn.rollback()
            return False

    def update_service_full(self, service_id, name, description, price, teacher_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE services
                    SET name=%s, description=%s, price=%s, teacher_name=%s
                    WHERE id=%s
                """, (name, description, price, teacher_name, service_id))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при update_service_full: {e}")
            self.conn.rollback()
            return False

    def get_all_teachers(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE user_type = 'teacher'")
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при get_all_teachers: {e}")
            return []

    def enroll_child_to_service(self, child_name, service_id):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT id FROM services WHERE id = %s", (service_id,))
                if not cursor.fetchone():
                    print(f"Сервис {service_id} не найден")
                    return False

                cursor.execute(
                    "SELECT id FROM service_enrollments WHERE child_name = %s AND service_id = %s",
                    (child_name, service_id)
                )
                if cursor.fetchone():
                    return False

                cursor.execute(
                    "INSERT INTO service_enrollments (child_name, service_id) VALUES (%s, %s)",
                    (child_name, service_id)
                )
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка записи на кружок: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def unenroll_child_from_service(self, child_name, service_id):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM service_enrollments
                    WHERE child_name = %s AND service_id = %s
                """, (child_name, service_id))

                deleted_count = cursor.rowcount

                self.conn.commit()

                return deleted_count > 0

        except Exception as e:
            print(f"Ошибка выписки ребенка из услуги: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def get_child_service_ids(self, child_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT service_id FROM service_enrollments WHERE child_name = %s",
                    (child_name,)
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка получения id услуг для ребёнка: {e}")
            return []

    def get_child_services(self, child_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT s.id, s.name, s.description, s.price, s.teacher_name
                    FROM service_enrollments e
                    JOIN services s ON e.service_id = s.id
                    WHERE e.child_name = %s
                """, (child_name,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения услуг ребенка: {e}")
            return []

    def get_enrolled_children_by_service(self, service_id):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT e.child_name
                    FROM service_enrollments e
                    JOIN users u ON e.child_name = u.child_name AND u.user_type = 'parent'
                    WHERE e.service_id = %s
                    ORDER BY e.child_name
                """, (service_id,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка получения записанных детей: {e}")
            return []

    def get_enrolled_children_by_teacher(self, teacher_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT e.child_name
                    FROM service_enrollments e
                    JOIN services s ON e.service_id = s.id
                    JOIN users u ON e.child_name = u.child_name AND u.user_type = 'parent'
                    WHERE s.teacher_name = %s
                    ORDER BY e.child_name
                """, (teacher_name,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка получения детей по учителю: {e}")
            return []

    def mark_attendance(self, child_name, service_id, date, status, reason, group_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM attendance
                    WHERE child_name=%s AND service_id=%s AND date=%s
                """, (child_name, service_id, date))
                row = cursor.fetchone()

                if row:
                    cursor.execute("""
                        UPDATE attendance SET status=%s, reason=%s WHERE id=%s
                    """, (status, reason, row[0]))
                else:
                    cursor.execute("""
                        INSERT INTO attendance (child_name, service_id, date, status, reason, group_name)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (child_name, service_id, date, status, reason, group_name))

                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка mark_attendance: {e}")
            self.conn.rollback()
            return False

    def delete_attendance(self, child_name, service_id, date_str):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM attendance WHERE child_name = %s AND service_id = %s AND date = %s",
                    (child_name, service_id, date_str)
                )
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при удалении отметки: {e}")
            self.conn.rollback()
            return False

    def get_attendance(self, child_name=None, group_name=None, date=None):
        try:
            with self.conn.cursor() as cursor:
                if child_name:
                    cursor.execute("SELECT * FROM attendance WHERE child_name = %s", (child_name,))
                elif group_name and date:
                    cursor.execute("SELECT * FROM attendance WHERE group_name = %s AND date = %s", (group_name, date))
                else:
                    cursor.execute("SELECT * FROM attendance")
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения посещаемости: {e}")
            return []

    def get_attendance_by_child_and_month(self, child_name, month, year):
        try:
            import calendar as _cal
            first_day = f"{year}-{month:02d}-01"
            last_day_num = _cal.monthrange(year, month)[1]
            last_day = f"{year}-{month:02d}-{last_day_num:02d}"

            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT date, status FROM attendance WHERE child_name = %s AND date BETWEEN %s AND %s",
                    (child_name, first_day, last_day)
                )
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            print(f"Ошибка получения посещаемости по месяцу: {e}")
            return {}

    def get_services_by_teacher(self, teacher_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name FROM services WHERE teacher_name = %s",
                    (teacher_name,)
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка get_services_by_teacher: {e}")
            return []

    def is_service_in_group(self, service_id, group_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT e.child_name
                    FROM service_enrollments e
                    JOIN users u ON e.child_name = u.child_name
                    WHERE e.service_id = %s AND u.group_name = %s
                    LIMIT 1
                """, (service_id, group_name))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Ошибка is_service_in_group: {e}")
            return False

    def get_children_by_group(self, group_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT u.child_name
                    FROM users u
                    WHERE u.group_name = %s
                      AND u.user_type = 'parent'
                      AND u.child_name IS NOT NULL
                    ORDER BY u.child_name
                """, (group_name,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка получения детей по группе: {e}")
            return []

    def get_child_full_info(self, child_name):
        """
        Возвращает полную информацию о ребенке, родителе и кружках.
        Нужно для интерфейса воспитателя.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        child_name,
                        child_birthdate,
                        group_name,
                        full_name,
                        parent_phone
                    FROM users
                    WHERE child_name = %s
                      AND user_type = 'parent'
                    LIMIT 1
                """, (child_name,))

                child_row = cursor.fetchone()

                if not child_row:
                    return None

                child_name_db, child_birthdate, group_name, parent_name, parent_phone = child_row

                age_text = self.format_child_age(child_birthdate) if child_birthdate else ""

                cursor.execute("""
                    SELECT
                        s.id,
                        s.name,
                        s.description,
                        s.price,
                        s.teacher_name
                    FROM service_enrollments e
                    JOIN services s ON e.service_id = s.id
                    WHERE e.child_name = %s
                    ORDER BY s.name
                """, (child_name,))

                services = cursor.fetchall()

                return {
                    "child_name": child_name_db,
                    "child_birthdate": str(child_birthdate) if child_birthdate else "",
                    "child_age": age_text,
                    "group_name": group_name or "",
                    "parent_name": parent_name or "",
                    "parent_phone": parent_phone or "",
                    "services": services
                }

        except Exception as e:
            print(f"Ошибка получения полной информации о ребенке: {e}")
            print(traceback.format_exc())
            return None

    def get_services_by_teacher_full(self, teacher_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, description, price, teacher_name
                    FROM services
                    WHERE teacher_name = %s
                """, (teacher_name,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка get_services_by_teacher_full: {e}")
            return []

    def get_parent_children(self, parent_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT child_name, group_name, parent_phone, child_birthdate
                    FROM users
                    WHERE full_name = %s
                      AND user_type = 'parent'
                      AND child_name IS NOT NULL
                    ORDER BY child_name
                """, (parent_name,))

                rows = cursor.fetchall()
                result = []

                for child_name, group_name, parent_phone, child_birthdate in rows:
                    age_text = self.format_child_age(child_birthdate) if child_birthdate else ""

                    result.append([
                        child_name,
                        group_name,
                        parent_phone,
                        str(child_birthdate) if child_birthdate else "",
                        age_text
                    ])

                return result

        except Exception as e:
            print(f"Ошибка получения детей родителя: {e}")
            return []

    def get_children_by_parent(self, parent_name):
        return self.get_parent_children(parent_name)

    def add_child_to_parent(self, parent_name, child_name, parent_phone=None, child_birthdate=None):
        try:
            if not parent_name or not child_name or not child_birthdate:
                return False

            group_name, group_type = self.get_child_group_by_birthdate(child_birthdate)

            if not group_name:
                print(group_type)
                return False

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id
                    FROM users
                    WHERE full_name = %s
                      AND child_name = %s
                      AND user_type = 'parent'
                """, (parent_name, child_name))

                if cursor.fetchone():
                    return False

                cursor.execute("""
                    SELECT username, parent_phone
                    FROM users
                    WHERE full_name = %s
                      AND user_type = 'parent'
                    LIMIT 1
                """, (parent_name,))

                parent_row = cursor.fetchone()

                if not parent_row:
                    return False

                parent_username = parent_row[0]
                existing_parent_phone = parent_row[1]

                if not parent_phone:
                    parent_phone = existing_parent_phone

                if not parent_phone:
                    return False

                child_count = len(self.get_parent_children(parent_name))

                safe_child_name = (
                    child_name
                    .lower()
                    .replace(" ", "_")
                    .replace(".", "")
                    .replace(",", "")
                )

                child_username = f"{parent_username}_{safe_child_name}_{child_count + 1}"
                temp_password = hashlib.sha256("123456".encode()).hexdigest()

                cursor.execute("""
                    INSERT INTO users (
                        username,
                        password,
                        user_type,
                        full_name,
                        child_name,
                        group_name,
                        parent_phone,
                        child_birthdate
                    )
                    VALUES (%s, %s, 'parent', %s, %s, %s, %s, %s)
                """, (
                    child_username,
                    temp_password,
                    parent_name,
                    child_name,
                    group_name,
                    parent_phone,
                    child_birthdate
                ))

                self.conn.commit()
                return True

        except Exception as e:
            print(f"Ошибка добавления ребенка: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def add_child_to_existing_parent(self, parent_id, child_name, parent_phone=None, child_birthdate=None):
        try:
            if not parent_id or not child_name or not child_birthdate:
                return False

            group_name, group_type = self.get_child_group_by_birthdate(child_birthdate)

            if not group_name:
                print(group_type)
                return False

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT username, full_name, parent_phone
                    FROM users
                    WHERE id = %s AND user_type = 'parent'
                """, (parent_id,))

                parent = cursor.fetchone()

                if not parent:
                    return False

                parent_username, parent_name, existing_parent_phone = parent

                if not parent_phone:
                    parent_phone = existing_parent_phone

                if not parent_phone:
                    return False

                child_count = len(self.get_parent_children(parent_name))

                safe_child_name = (
                    child_name
                    .lower()
                    .replace(" ", "_")
                    .replace(".", "")
                    .replace(",", "")
                )

                child_username = f"{parent_username}_{safe_child_name}_{child_count + 1}"
                temp_password = hashlib.sha256("123456".encode()).hexdigest()

                cursor.execute("""
                    INSERT INTO users (
                        username,
                        password,
                        user_type,
                        full_name,
                        child_name,
                        group_name,
                        parent_phone,
                        child_birthdate
                    )
                    VALUES (%s, %s, 'parent', %s, %s, %s, %s, %s)
                """, (
                    child_username,
                    temp_password,
                    parent_name,
                    child_name,
                    group_name,
                    parent_phone,
                    child_birthdate
                ))

                self.conn.commit()
                return True

        except Exception as e:
            print(f"Ошибка добавления ребенка к существующему родителю: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def get_total_payment_for_parent(self, parent_name):
        try:
            total = 0
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT child_name FROM users
                    WHERE full_name = %s AND user_type = 'parent' AND child_name IS NOT NULL
                """, (parent_name,))
                children = cursor.fetchall()

                for child_row in children:
                    child_name = child_row[0]
                    child_services = self.get_child_services(child_name)

                    for service in child_services:
                        service_id = service[0]
                        price = float(service[3])

                        cursor.execute("""
                            SELECT COUNT(*) FROM attendance
                            WHERE child_name = %s AND service_id = %s AND status = 'присутствовал'
                        """, (child_name, service_id))
                        count_present = cursor.fetchone()[0]
                        total += count_present * price

            return total
        except Exception as e:
            print(f"Ошибка расчета общей стоимости: {e}")
            return 0

    def update_child(self, parent_name, old_child_name, new_child_name, child_birthdate=None, parent_phone=None):
        try:
            if not parent_name or not old_child_name or not new_child_name:
                return False

            group_name = None

            if child_birthdate:
                group_name, group_type = self.get_child_group_by_birthdate(child_birthdate)

                if not group_name:
                    print(group_type)
                    return False

            with self.conn.cursor() as cursor:
                if child_birthdate:
                    cursor.execute("""
                        UPDATE users
                        SET child_name = %s,
                            group_name = %s,
                            child_birthdate = %s,
                            parent_phone = COALESCE(%s, parent_phone)
                        WHERE full_name = %s
                          AND child_name = %s
                          AND user_type = 'parent'
                    """, (
                        new_child_name,
                        group_name,
                        child_birthdate,
                        parent_phone,
                        parent_name,
                        old_child_name
                    ))
                else:
                    cursor.execute("""
                        UPDATE users
                        SET child_name = %s,
                            parent_phone = COALESCE(%s, parent_phone)
                        WHERE full_name = %s
                          AND child_name = %s
                          AND user_type = 'parent'
                    """, (
                        new_child_name,
                        parent_phone,
                        parent_name,
                        old_child_name
                    ))

                cursor.execute("""
                    UPDATE attendance
                    SET child_name = %s
                    WHERE child_name = %s
                """, (new_child_name, old_child_name))

                cursor.execute("""
                    UPDATE service_enrollments
                    SET child_name = %s
                    WHERE child_name = %s
                """, (new_child_name, old_child_name))

                self.conn.commit()
                return True

        except Exception as e:
            print(f"Ошибка при обновлении ребенка: {e}")
            print(traceback.format_exc())
            self.conn.rollback()
            return False

    def rename_child_all_tables(self, old_child_name, new_child_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users SET child_name = %s
                    WHERE child_name = %s AND user_type = 'parent'
                """, (new_child_name, old_child_name))

                cursor.execute("""
                    UPDATE attendance SET child_name = %s
                    WHERE child_name = %s
                """, (new_child_name, old_child_name))

                cursor.execute("""
                    UPDATE service_enrollments SET child_name = %s
                    WHERE child_name = %s
                """, (new_child_name, old_child_name))

                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при переименовании ребенка: {e}")
            self.conn.rollback()
            return False

    def delete_child(self, parent_name, child_name):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM users
                    WHERE full_name = %s AND child_name = %s AND user_type = 'parent'
                """, (parent_name, child_name))

                cursor.execute("DELETE FROM attendance WHERE child_name = %s", (child_name,))
                cursor.execute("DELETE FROM service_enrollments WHERE child_name = %s", (child_name,))

                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при удалении ребенка: {e}")
            self.conn.rollback()
            return False

    def add_sample_data(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM services")
                services_count = cursor.fetchone()[0]

                if users_count == 0 and services_count == 0:
                    test_users = [
                        ("admin", "admin", "admin", "Администратор Системы", None, "Все группы", None, None),
                        ("ivanova", "1", "teacher", "Иванова А.П.", None, "Непоседы", None, None),
                        ("petrov", "1", "parent", "Петров Иван Сергеевич", "Маша Петрова", "Непоседы",
                         "+7 900 111-22-33", "2023-04-15"),
                        ("sidorova", "1", "parent", "Сидорова Мария Ивановна", "Коля Сидоров", "Буратино",
                         "+7 900 222-33-44", "2021-08-10"),
                    ]

                    for username, password, user_type, full_name, child_name, group_name, parent_phone, child_birthdate in test_users:
                        hashed_password = hashlib.sha256(password.encode()).hexdigest()

                        if user_type == "parent" and child_birthdate:
                            auto_group, group_type = self.get_child_group_by_birthdate(child_birthdate)
                            if auto_group:
                                group_name = auto_group

                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO users (
                                    username, password, user_type, full_name, child_name, group_name, parent_phone, child_birthdate
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                username,
                                hashed_password,
                                user_type,
                                full_name,
                                child_name,
                                group_name,
                                parent_phone,
                                child_birthdate
                            ))

                    sample_services = [
                        ("Рисование", "Занятия по рисованию для детей", 1500.0, "Иванова А.П."),
                        ("Танцы", "Танцевальный кружок", 2000.0, "Иванова А.П."),
                        ("Английский язык", "Изучение английского в игровой форме", 2500.0, "Иванова А.П.")
                    ]

                    for service in sample_services:
                        cursor.execute("SELECT id FROM services WHERE name = %s", (service[0],))
                        if not cursor.fetchone():
                            cursor.execute("""
                                INSERT INTO services (name, description, price, teacher_name)
                                VALUES (%s, %s, %s, %s)
                            """, service)

                self.conn.commit()
        except Exception as e:
            print(f"Ошибка добавления тестовых данных: {e}")
            print(traceback.format_exc())
            self.conn.rollback()

