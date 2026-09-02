import flet as ft
from database import KindergartenDB
from datetime import datetime
import calendar
import os
import subprocess
import platform


class TeacherInterface:
    def __init__(self, page, user, db: KindergartenDB):
        self.page = page
        self.user = user
        self.db = db

        self.current_attendance_status = None
        self.current_selected_date = None

        self.current_child = None
        self.current_service_id = None
        self.current_month = datetime.now().month
        self.current_year = datetime.now().year

        self.calendar_container = None
        self.child_dropdown = None
        self.service_dropdown = None
        self.month_dropdown = None
        self.year_field = None

        self.teacher_children = []
        self.teacher_services = []
        self.all_teacher_services = []

    # =========================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================
    def only_digits(self, value, max_len=None):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if max_len:
            digits = digits[:max_len]
        return digits

    def format_phone_value(self, value):
        """
        88005553535 -> 8 800 555 35 35
        """
        digits = self.only_digits(value, 11)

        if len(digits) <= 1:
            return digits
        if len(digits) <= 4:
            return f"{digits[:1]} {digits[1:]}"
        if len(digits) <= 7:
            return f"{digits[:1]} {digits[1:4]} {digits[4:]}"
        if len(digits) <= 9:
            return f"{digits[:1]} {digits[1:4]} {digits[4:7]} {digits[7:]}"
        return f"{digits[:1]} {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"

    def copy_to_clipboard(self, text):
        try:
            if not text:
                self.show_message("Нечего копировать", ft.Colors.ORANGE)
                return

            text = self.format_phone_value(text)

            if hasattr(self.page, "set_clipboard"):
                self.page.set_clipboard(text)
                self.show_message("Номер телефона скопирован", ft.Colors.GREEN)
                return

            system = platform.system()

            if system == "Windows":
                subprocess.run(
                    "clip",
                    input=text,
                    text=True,
                    shell=True,
                    check=True
                )
            elif system == "Darwin":
                subprocess.run(
                    ["pbcopy"],
                    input=text,
                    text=True,
                    check=True
                )
            elif system == "Linux":
                try:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text,
                        text=True,
                        check=True
                    )
                except Exception:
                    subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=text,
                        text=True,
                        check=True
                    )
            else:
                raise Exception("Буфер обмена не поддерживается для этой ОС")

            self.show_message("Номер телефона скопирован", ft.Colors.GREEN)

        except Exception as e:
            print(f"Ошибка копирования: {e}")
            self.show_message("Не удалось скопировать номер", ft.Colors.RED)

    def calculate_age_text(self, birthdate):
        try:
            if not birthdate:
                return "-"

            birthdate = str(birthdate).strip()

            dt = None

            for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y"):
                try:
                    dt = datetime.strptime(birthdate, fmt)
                    break
                except Exception:
                    pass

            if dt is None:
                return "-"

            today = datetime.now()
            years = today.year - dt.year
            months = today.month - dt.month

            if today.day < dt.day:
                months -= 1

            if months < 0:
                years -= 1
                months += 12

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

        except Exception:
            return "-"

    def format_birthdate_for_view(self, birthdate):
        try:
            if not birthdate:
                return "-"

            birthdate = str(birthdate).strip()

            for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y"):
                try:
                    return datetime.strptime(birthdate, fmt).strftime("%d.%m.%Y")
                except Exception:
                    pass

            digits = self.only_digits(birthdate, 8)

            if len(digits) == 8:
                try:
                    dt = datetime.strptime(
                        f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}",
                        "%Y-%m-%d"
                    )
                    return dt.strftime("%d.%m.%Y")
                except Exception:
                    pass

                try:
                    dt = datetime.strptime(
                        f"{digits[4:8]}-{digits[2:4]}-{digits[:2]}",
                        "%Y-%m-%d"
                    )
                    return dt.strftime("%d.%m.%Y")
                except Exception:
                    pass

            return birthdate

        except Exception:
            return "-"

    def normalize_year_value(self, value):

        try:
            year = int(str(value or "").strip())
        except Exception:
            return datetime.now().year

        if year < 2025:
            return 2025

        if year > 2026:
            return 2026

        return year

    def setup_year_field(self, field):
        """
        Разрешает вводить только цифры и максимум 4 символа.
        Год не исправляется сразу, чтобы можно было спокойно набрать 2026.
        """

        def on_year_change(e):
            value = str(field.value or "")
            digits = "".join(ch for ch in value if ch.isdigit())

            if len(digits) > 4:
                digits = digits[:4]

            if field.value != digits:
                field.value = digits
                field.update()

        field.on_change = on_year_change
        return field

    def get_db_connection(self):
        for attr in ["conn", "connection", "db", "_conn", "_connection"]:
            conn = getattr(self.db, attr, None)
            if conn:
                return conn
        return None

    def get_db_cursor(self):
        try:
            if hasattr(self.db, "cursor") and self.db.cursor:
                return self.db.cursor

            conn = self.get_db_connection()
            if conn:
                return conn.cursor()

            return None
        except Exception:
            return None

    def table_exists(self, cursor, table_name):
        try:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return cursor.fetchone() is not None
        except Exception:
            return False

    def get_table_columns(self, cursor, table_name):
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            rows = cursor.fetchall()
            return [row[1] for row in rows]
        except Exception:
            return []

    def get_child_full_info(self, child_name):
        """
        Возвращает полную информацию по ребенку.
        Код сделан с запасом: сначала пытается использовать методы БД,
        потом пробует достать данные напрямую из SQLite.
        """
        info = {
            "child_name": child_name,
            "group_name": "-",
            "birthdate": "-",
            "age": "-",
            "parent_name": "-",
            "parent_phone": "-",
            "services": [],
        }

        # 1. Кружки ребенка
        try:
            services = self.db.get_child_services(child_name) or []
            info["services"] = services
        except Exception as e:
            print(f"Ошибка get_child_services: {e}")

        # 2. Если в БД есть отдельный метод get_child_full_info
        try:
            if hasattr(self.db, "get_child_full_info"):
                data = self.db.get_child_full_info(child_name)

                if isinstance(data, dict):
                    info.update({
                        "child_name": data.get("child_name", info["child_name"]),
                        "group_name": data.get("group_name", info["group_name"]),
                        "birthdate": data.get("child_birthdate", data.get("birthdate", info["birthdate"])),
                        "age": data.get("child_age", data.get("age", info["age"])),
                        "parent_name": data.get("parent_name", data.get("full_name", info["parent_name"])),

                        "parent_phone": data.get("parent_phone", data.get("phone", info["parent_phone"])),
                    })
                    return info

                if isinstance(data, (list, tuple)) and len(data) > 0:
                    # Поддержка возможного формата:
                    # child_name, group_name, parent_phone, child_birthdate, child_age, parent_name, username
                    if len(data) > 0:
                        info["child_name"] = data[0] or info["child_name"]
                    if len(data) > 1:
                        info["group_name"] = data[1] or info["group_name"]
                    if len(data) > 2:
                        info["parent_phone"] = data[2] or info["parent_phone"]
                    if len(data) > 3:
                        info["birthdate"] = data[3] or info["birthdate"]
                    if len(data) > 4:
                        info["age"] = data[4] or info["age"]
                    if len(data) > 5:
                        info["parent_name"] = data[5] or info["parent_name"]

                    return info

        except Exception as e:
            print(f"Ошибка get_child_full_info: {e}")

        # 3. Пробуем получить данные через таблицу users
        try:
            cursor = self.get_db_cursor()

            if cursor and self.table_exists(cursor, "users"):
                columns = self.get_table_columns(cursor, "users")

                select_columns = []

                for column in [
                    "username",
                    "full_name",
                    "child_name",
                    "group_name",
                    "parent_phone",
                    "child_birthdate",
                    "child_age",
                    "user_type"
                ]:
                    if column in columns:
                        select_columns.append(column)

                if select_columns:
                    query = f"""
                        SELECT {", ".join(select_columns)}
                        FROM users
                        WHERE child_name = ?
                    """

                    if "user_type" in columns:
                        query += " AND user_type = 'parent'"

                    cursor.execute(query, (child_name,))
                    row = cursor.fetchone()

                    if row:
                        row_dict = dict(zip(select_columns, row))

                        info["parent_name"] = row_dict.get("full_name") or info["parent_name"]
                        info["child_name"] = row_dict.get("child_name") or info["child_name"]
                        info["group_name"] = row_dict.get("group_name") or info["group_name"]
                        info["parent_phone"] = row_dict.get("parent_phone") or info["parent_phone"]
                        info["birthdate"] = row_dict.get("child_birthdate") or info["birthdate"]
                        info["age"] = row_dict.get("child_age") or info["age"]

        except Exception as e:
            print(f"Ошибка прямого чтения users: {e}")

        # 4. Пробуем получить данные через таблицу children, если она есть
        try:
            cursor = self.get_db_cursor()

            if cursor and self.table_exists(cursor, "children"):
                columns = self.get_table_columns(cursor, "children")

                possible_name_columns = ["child_name", "name", "full_name"]
                name_column = None

                for col in possible_name_columns:
                    if col in columns:
                        name_column = col
                        break

                if name_column:
                    select_columns = []

                    for column in [
                        "child_name",
                        "name",
                        "group_name",
                        "parent_phone",
                        "phone",
                        "child_birthdate",
                        "birthdate",
                        "child_age",
                        "age",
                        "parent_name",
                        "parent_full_name"
                    ]:
                        if column in columns:
                            select_columns.append(column)

                    if select_columns:
                        query = f"""
                            SELECT {", ".join(select_columns)}
                            FROM children
                            WHERE {name_column} = ?
                        """

                        cursor.execute(query, (child_name,))
                        row = cursor.fetchone()

                        if row:
                            row_dict = dict(zip(select_columns, row))

                            info["child_name"] = (
                                row_dict.get("child_name")
                                or row_dict.get("name")
                                or info["child_name"]
                            )
                            info["group_name"] = row_dict.get("group_name") or info["group_name"]
                            info["parent_phone"] = (
                                row_dict.get("parent_phone")
                                or row_dict.get("phone")
                                or info["parent_phone"]
                            )
                            info["birthdate"] = (
                                row_dict.get("child_birthdate")
                                or row_dict.get("birthdate")
                                or info["birthdate"]
                            )
                            info["age"] = (
                                row_dict.get("child_age")
                                or row_dict.get("age")
                                or info["age"]
                            )
                            info["parent_name"] = (
                                row_dict.get("parent_name")
                                or row_dict.get("parent_full_name")
                                or info["parent_name"]
                            )

        except Exception as e:
            print(f"Ошибка прямого чтения children: {e}")

        if info.get("birthdate") and info.get("birthdate") != "-":
            info["age"] = self.calculate_age_text(info["birthdate"])
        elif not info["age"] or info["age"] == "-":
            info["age"] = "-"

        info["parent_phone"] = self.format_phone_value(info["parent_phone"])

        return info

    def show_child_info_dialog(self, child_name):
        info = self.get_child_full_info(child_name)

        parent_phone = self.format_phone_value(info.get("parent_phone"))

        services = info.get("services") or []
        if services:
            service_lines = []

            for service in services:
                try:
                    # Возможный формат: id, name, description, price, teacher
                    if len(service) >= 2:
                        service_lines.append(f"• {service[1]}")
                    else:
                        service_lines.append(f"• {service}")
                except Exception:
                    service_lines.append(f"• {service}")

            services_text = "\n".join(service_lines)
        else:
            services_text = "Не записан на кружки"

        phone_row = ft.Row(
            [
                ft.Text(
                    f"Телефон: {parent_phone or '-'}",
                    size=14,
                    selectable=True,
                    expand=True
                ),
                ft.IconButton(
                    icon=ft.Icons.COPY,
                    tooltip="Скопировать телефон",
                    icon_color=ft.Colors.BLUE,
                    on_click=lambda e: self.copy_to_clipboard(parent_phone)
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Информация о ребенке", weight="bold"),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    [
                        ft.Text("Ребенок", size=16, weight="bold", color=ft.Colors.BLUE_800),
                        ft.Text(f"ФИО: {info.get('child_name') or '-'}", size=14, selectable=True),
                        ft.Text(f"Группа: {info.get('group_name') or '-'}", size=14, selectable=True),
                        ft.Text(
                            f"Дата рождения: {self.format_birthdate_for_view(info.get('birthdate'))}",
                            size=14,
                            selectable=True
                        ),
                        ft.Text(f"Возраст: {info.get('age') or '-'}", size=14, selectable=True),

                        ft.Divider(height=20),

                        ft.Text("Родитель", size=16, weight="bold", color=ft.Colors.GREEN_800),
                        ft.Text(f"ФИО родителя: {info.get('parent_name') or '-'}", size=14, selectable=True),
                        phone_row,

                        ft.Divider(height=20),

                        ft.Text("Кружки", size=16, weight="bold", color=ft.Colors.PURPLE_800),
                        ft.Text(services_text, size=13, color=ft.Colors.GREY_800, selectable=True),
                    ],
                    spacing=8,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO
                )
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda e: self.close_dialog(dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.open_dialog(dialog)

    # =========================
    # ОСНОВНОЕ МЕНЮ
    # =========================
    def show_interface(self):
        self.page.clean()
        self.page.title = f"Воспитатель: {self.user[4]}"
        self.page.bgcolor = "#EEF3F8"

        logout_button = ft.IconButton(
            icon=ft.Icons.LOGOUT,
            tooltip="Выйти из аккаунта",
            icon_color=ft.Colors.RED,
            on_click=lambda e: self.confirm_logout(),
        )

        top_bar = ft.Row(
            [
                ft.Container(expand=True),
                logout_button,
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        user_info = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"Воспитатель: {self.user[4]}",
                        size=18,
                        weight="bold",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"Группа: {self.user[6]}",
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.GREY_700,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=20,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=14,
            bgcolor=ft.Colors.WHITE,
            width=400,
        )

        calendar_button = ft.ElevatedButton(
            "📅 Календарь посещаемости",
            on_click=lambda e: self.show_attendance_calendar(),
            width=300,
            height=52,
        )

        children_button = ft.ElevatedButton(
            "👥 Список детей в группе",
            on_click=lambda e: self.show_group_children(),
            width=300,
            height=52,
        )

        services_button = ft.ElevatedButton(
            "🎨 Мои кружки",
            on_click=lambda e: self.show_my_services(),
            width=300,
            height=52,
        )

        menu = ft.Container(
            content=ft.Column(
                [
                    user_info,
                    calendar_button,
                    children_button,
                    services_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=18,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        top_bar,
                        menu,
                    ],
                    expand=True,
                ),
                bgcolor="#EEF3F8",
                padding=20,
                expand=True,
            )
        )

        self.page.update()

    def confirm_logout(self):
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Выход из аккаунта"),
            content=ft.Text("Вы действительно хотите выйти из аккаунта?"),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda e: self.close_dialog(dialog),
                ),
                ft.ElevatedButton(
                    "Выйти",
                    on_click=lambda e: self.logout_confirmed(dialog),
                    bgcolor=ft.Colors.RED_100,
                    color=ft.Colors.RED,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.open_dialog(dialog)

    def logout_confirmed(self, dialog):
        self.close_dialog(dialog)
        from main import logout_user
        logout_user(self.page, self.db)

    def open_dialog(self, dialog):
        try:
            if hasattr(self.page, "overlay"):
                if dialog not in self.page.overlay:
                    self.page.overlay.append(dialog)
            else:
                self.page.dialog = dialog

            dialog.open = True
            self.page.update()
        except Exception as e:
            print(f"Ошибка при открытии диалога: {e}")

    def close_dialog(self, dialog):
        try:
            dialog.open = False
            self.page.update()
        except Exception as e:
            print(f"Ошибка при закрытии диалога: {e}")

    # =========================
    # СПИСОК ДЕТЕЙ
    # =========================
    def show_group_children(self):
        self.page.clean()
        self.page.title = "Дети в группе"
        self.page.bgcolor = "#EEF3F8"

        group_name = self.user[6]
        children = self.db.get_children_by_group(group_name) or []

        back_button = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK
        )

        if not children:
            self.page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Дети в группе", size=20, weight="bold"),
                            ft.Divider(height=20),
                            ft.Text("В группе нет детей", size=16, color=ft.Colors.GREY),
                            ft.Divider(height=20),
                            back_button
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=20,
                    expand=True
                )
            )
            self.page.update()
            return

        children_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8)

        for child in children:
            child_services = []

            try:
                child_services = self.db.get_child_services(child) or []
            except Exception as e:
                print(f"Ошибка get_child_services для {child}: {e}")

            if child_services:
                service_names = []

                for service in child_services:
                    try:
                        service_names.append(f"• {service[1]}")
                    except Exception:
                        service_names.append(f"• {service}")

                services_text = "\n".join(service_names)
            else:
                services_text = "Не записан на кружки"

            child_info = self.get_child_full_info(child)
            phone = self.format_phone_value(child_info.get("parent_phone"))

            card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        child,
                                        size=16,
                                        weight="bold",
                                        color=ft.Colors.BLUE,
                                        expand=True
                                    ),
                                    ft.Icon(
                                        ft.Icons.INFO_OUTLINE,
                                        color=ft.Colors.BLUE_400,
                                        size=20
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Text(
                                f"Родитель: {child_info.get('parent_name') or '-'}",
                                size=12,
                                color=ft.Colors.GREY_700
                            ),
                            ft.Row(
                                [
                                    ft.Text(
                                        f"Телефон: {phone or '-'}",
                                        size=12,
                                        color=ft.Colors.GREY_700,
                                        expand=True
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.COPY,
                                        icon_size=16,
                                        tooltip="Скопировать телефон",
                                        on_click=lambda e, p=phone: self.copy_to_clipboard(p)
                                    )
                                ],
                                spacing=5,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER
                            ),
                            ft.Text("Кружки:", size=14, weight="bold"),
                            ft.Text(services_text, size=12, color=ft.Colors.GREY_700),

                        ],
                        spacing=5
                    ),
                    padding=15,
                    width=500,
                    border_radius=10,
                    on_click=lambda e, ch=child: self.show_child_info_dialog(ch)
                )
            )

            children_list.controls.append(card)

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"Дети в группе '{group_name}'", size=20, weight="bold"),
                        ft.Divider(height=20),
                        ft.Container(
                            content=children_list,
                            height=500,
                            width=540,
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=12,
                            padding=10,
                            bgcolor=ft.Colors.WHITE
                        ),
                        ft.Divider(height=20),
                        back_button
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.ADAPTIVE
                ),
                alignment=ft.Alignment.CENTER,
                padding=20,
                expand=True
            )
        )
        self.page.update()

    # =========================
    # МОИ КРУЖКИ
    # =========================
    def show_my_services(self):
        self.page.clean()
        self.page.title = "Мои кружки"
        self.page.bgcolor = "#EEF3F8"

        teacher_name = self.user[4]
        services = self.db.get_services_by_teacher_full(teacher_name) or []

        back_button = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK
        )

        if not services:
            self.page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Мои кружки", size=20, weight="bold"),
                            ft.Divider(height=20),
                            ft.Text("У вас нет назначенных кружков", size=16, color=ft.Colors.GREY),
                            ft.Divider(height=20),
                            back_button
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=20,
                    expand=True
                )
            )
            self.page.update()
            return

        services_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8)

        for service in services:
            service_id, name, description, price, teacher = service
            enrolled_children = self.db.get_enrolled_children_by_service(service_id) or []

            if enrolled_children:
                child_rows = []

                for child in enrolled_children:
                    child_rows.append(
                        ft.Row(
                            [
                                ft.Text(f"• {child}", size=12, expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.INFO_OUTLINE,
                                    icon_size=16,
                                    tooltip="Информация о ребенке",
                                    on_click=lambda e, ch=child: self.show_child_info_dialog(ch)
                                )
                            ],
                            spacing=5
                        )
                    )

                children_content = ft.Column(child_rows, spacing=2)
            else:
                children_content = ft.Text("Нет записанных детей", size=11, color=ft.Colors.GREY_700)

            services_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(name, size=16, weight="bold", color=ft.Colors.GREEN),
                                ft.Text(description or "Нет описания", size=12),
                                ft.Text(f"💵 Стоимость: {price} руб./мес", size=12, weight="bold"),
                                ft.Divider(height=10),
                                ft.Text(f"👥 Записано детей ({len(enrolled_children)}):", size=12, weight="bold"),
                                children_content
                            ],
                            spacing=5
                        ),
                        padding=15,
                        width=520
                    )
                )
            )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Мои кружки", size=20, weight="bold"),
                        ft.Divider(height=20),
                        ft.Container(
                            content=services_list,
                            height=500,
                            width=560,
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=12,
                            padding=10,
                            bgcolor=ft.Colors.WHITE
                        ),
                        ft.Divider(height=20),
                        back_button
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.ADAPTIVE
                ),
                alignment=ft.Alignment.CENTER,
                padding=20,
                expand=True
            )
        )
        self.page.update()

    # =========================
    # КАЛЕНДАРЬ ПОСЕЩАЕМОСТИ
    # =========================
    def show_attendance_calendar(self):
        self.page.clean()
        self.page.title = "Календарь посещаемости"
        self.page.bgcolor = "#EEF3F8"

        group_name = self.user[6]

        self.teacher_children = self.db.get_children_by_group(group_name) or []
        print("GROUP CHILDREN =", self.teacher_children)

        if not self.teacher_children:
            self.show_message("В вашей группе нет детей.", ft.Colors.RED)
            self.show_interface()
            return

        self.all_teacher_services = self.db.get_services_by_teacher(self.user[4]) or []
        print("TEACHER SERVICES =", self.all_teacher_services)

        if not self.current_child or self.current_child not in self.teacher_children:
            self.current_child = self.teacher_children[0]

        months = [
            ("Январь", 1), ("Февраль", 2), ("Март", 3), ("Апрель", 4),
            ("Май", 5), ("Июнь", 6), ("Июль", 7), ("Август", 8),
            ("Сентябрь", 9), ("Октябрь", 10), ("Ноябрь", 11), ("Декабрь", 12)
        ]

        self.child_dropdown = ft.Dropdown(
            label="Выберите ребёнка",
            options=[ft.dropdown.Option(key=ch, text=ch) for ch in self.teacher_children],
            width=300,
            value=self.current_child,
        )

        self.child_dropdown.on_select = self.on_child_changed

        self.service_dropdown = ft.Dropdown(
            label="Кружок",
            options=[],
            width=300,
            value=None,
        )

        self.service_dropdown.on_select = self.on_service_changed

        month_value = f"{months[self.current_month - 1][0]} ({self.current_month})"
        self.month_dropdown = ft.Dropdown(
            label="Месяц",
            options=[ft.dropdown.Option(key=f"{name} ({num})", text=f"{name} ({num})") for name, num in months],
            width=300,
            value=month_value,
        )

        self.month_dropdown.on_select = self.on_month_changed

        self.year_field = self.setup_year_field(ft.TextField(
            label="Год",
            value=str(self.current_year),
            width=300,
        ))
        self.year_field.on_change = self.on_year_changed

        self.calendar_container = ft.Column()

        child_info_button = ft.ElevatedButton(
            "ℹ️ Информация о ребенке",
            on_click=lambda e: self.show_child_info_dialog(self.current_child),
            width=300,
            height=40,
            bgcolor=ft.Colors.BLUE_50,
            color=ft.Colors.BLUE
        )

        mass_buttons_row = ft.Row(
            [
                ft.ElevatedButton(
                    "✅ Отметить всех",
                    on_click=lambda e: self.mark_all_children(),
                    icon=ft.Icons.CHECK_CIRCLE,
                    bgcolor=ft.Colors.GREEN_100,
                    color=ft.Colors.GREEN,
                    height=40,
                ),
                ft.ElevatedButton(
                    "🔄 Сброс группы",
                    on_click=lambda e: self.reset_group_dates(),
                    icon=ft.Icons.REFRESH,
                    bgcolor=ft.Colors.GREY_100,
                    color=ft.Colors.GREY,
                    height=40,
                ),
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True,
        )

        mass_panel = ft.Container(
            content=ft.Column(
                [
                    mass_buttons_row,
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.Alignment.CENTER,
            padding=ft.padding.only(top=5, bottom=5)
        )

        back_button = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK
        )

        self.page.add(
            ft.Container(
                ft.Column(
                    [
                        ft.Text("Календарь посещаемости", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                        ft.Column(
                            [
                                self.child_dropdown,
                                child_info_button,
                                self.service_dropdown,
                                self.month_dropdown,
                                self.year_field,
                            ],
                            spacing=8,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),

                        mass_panel,

                        ft.Container(
                            content=self.calendar_container,
                            height=550,
                            width=480,
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=12,
                            padding=15,
                            bgcolor=ft.Colors.WHITE
                        ),
                        ft.Divider(height=20),
                        ft.Container(
                            content=back_button,
                            alignment=ft.Alignment.CENTER,
                            padding=ft.padding.only(top=10)
                        )
                    ],
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8
                ),
                alignment=ft.Alignment.CENTER,
                padding=20,
                expand=True
            )
        )

        self.refresh_services_for_child()
        self.refresh_calendar()
        self.page.update()

    def refresh_services_for_child(self):
        if not self.current_child:
            self.teacher_services = []
            self.current_service_id = None

            if self.service_dropdown:
                self.service_dropdown.options = []
                self.service_dropdown.value = None
                self.service_dropdown.update()

            return

        child_service_ids = set(self.db.get_child_service_ids(self.current_child) or [])
        print(f"CHILD '{self.current_child}' SERVICE IDS =", child_service_ids)

        filtered_services = []

        for service in self.all_teacher_services:
            service_id, service_name = service

            if service_id in child_service_ids:
                filtered_services.append(service)

        self.teacher_services = filtered_services
        print(f"FILTERED SERVICES FOR '{self.current_child}' =", self.teacher_services)

        if not self.service_dropdown:
            return

        self.service_dropdown.options = [
            ft.dropdown.Option(key=str(service_id), text=service_name)
            for service_id, service_name in self.teacher_services
        ]

        available_ids = [str(service_id) for service_id, service_name in self.teacher_services]

        if available_ids:
            self.current_service_id = available_ids[0]
            self.service_dropdown.value = self.current_service_id
        else:
            self.current_service_id = None
            self.service_dropdown.value = None

        self.service_dropdown.update()

    def on_child_changed(self, e):
        selected_child = None

        if hasattr(e, "data") and e.data:
            selected_child = str(e.data)
        elif e.control and e.control.value:
            selected_child = str(e.control.value)

        print("ON_CHILD_CHANGED ->", selected_child)

        if not selected_child:
            return

        self.current_child = selected_child
        self.current_selected_date = None
        self.current_attendance_status = None

        if self.child_dropdown:
            self.child_dropdown.value = selected_child
            self.child_dropdown.update()

        self.refresh_services_for_child()
        self.refresh_calendar()
        self.page.update()

    def on_service_changed(self, e):
        selected_service_id = None

        if hasattr(e, "data") and e.data:
            selected_service_id = str(e.data)
        elif e.control and e.control.value:
            selected_service_id = str(e.control.value)

        print("ON_SERVICE_CHANGED ->", selected_service_id)

        if not selected_service_id:
            return

        self.current_service_id = selected_service_id
        self.current_selected_date = None
        self.current_attendance_status = None

        if self.service_dropdown:
            self.service_dropdown.value = selected_service_id
            self.service_dropdown.update()

        self.refresh_calendar()
        self.page.update()

    def on_month_changed(self, e):
        try:
            self.current_month = int(e.control.value.split("(")[-1].strip(")"))
        except Exception:
            pass
        self.refresh_calendar()

    def on_year_changed(self, e):
        year_text = str(e.control.value or "").strip()

        # Пока пользователь не ввел 4 цифры, календарь не обновляем
        if len(year_text) < 4:
            return

        selected_year = self.normalize_year_value(year_text)

        self.current_year = selected_year

        if self.year_field and str(selected_year) != year_text:
            self.year_field.value = str(selected_year)
            self.year_field.update()

        self.refresh_calendar()
        self.page.update()

    def refresh_calendar(self):
        if not self.calendar_container:
            return

        self.calendar_container.controls.clear()

        child_name = self.current_child

        service_id = str(self.current_service_id) if self.current_service_id else None

        selected_month = self.current_month
        selected_year = self.normalize_year_value(self.current_year)
        self.current_year = selected_year

        if self.year_field:
            self.year_field.value = str(selected_year)

        print("REFRESH CALENDAR:")
        print("child_name =", child_name)
        print("service_id =", service_id)
        print("month =", selected_month)
        print("year =", selected_year)

        if not child_name:
            self.calendar_container.controls.append(
                ft.Text("Не выбран ребенок", color=ft.Colors.RED)
            )
            self.calendar_container.update()
            return

        if not service_id:
            self.calendar_container.controls.append(
                ft.Text("Этот ребенок не записан на кружки данного воспитателя", color=ft.Colors.RED)
            )
            self.calendar_container.update()
            return

        first_day = f"{selected_year}-{selected_month:02d}-01"
        last_day_num = calendar.monthrange(selected_year, selected_month)[1]
        last_day = f"{selected_year}-{selected_month:02d}-{last_day_num:02d}"

        rows = self.db.get_attendance_for_child_service_month(
            child_name,
            int(service_id),
            first_day,
            last_day
        )

        print("rows =", rows)

        attendance = {}
        for row in rows:
            date_str, status = row
            try:
                rec_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                attendance[rec_date] = status
            except Exception:
                try:
                    rec_date = datetime.strptime(date_str, "%Y%m%d").date()
                    attendance[rec_date] = status
                except Exception:
                    continue

        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        month_name = month_names[selected_month - 1]

        self.calendar_container.controls.append(
            ft.Container(
                content=ft.Text(
                    f"{month_name} {selected_year} — {child_name}",
                    size=18,
                    weight="bold",
                    color=ft.Colors.BLUE_800
                ),
                alignment=ft.Alignment.CENTER,
                padding=ft.padding.only(bottom=10)
            )
        )

        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_header_row = []

        for day_name in day_names:
            day_header_row.append(
                ft.Container(
                    content=ft.Text(
                        day_name,
                        size=12,
                        weight="bold",
                        color=ft.Colors.BLUE_GREY_700
                    ),
                    width=40,
                    height=30,
                    alignment=ft.Alignment.CENTER,
                    border=ft.Border.all(0.5, ft.Colors.GREY_300)
                )
            )

        self.calendar_container.controls.append(
            ft.Row(day_header_row, spacing=0, alignment=ft.MainAxisAlignment.CENTER)
        )
        self.calendar_container.controls.append(ft.Divider(height=5, color=ft.Colors.TRANSPARENT))

        cal = calendar.Calendar()
        weeks = list(cal.monthdatescalendar(selected_year, selected_month))

        for week in weeks:
            week_row = []

            for d in week:
                if d.month != selected_month:
                    bg_color = ft.Colors.GREY_100
                    text_color = ft.Colors.GREY_400
                    border_color = ft.Colors.GREY_200
                elif d.weekday() >= 5:
                    bg_color = ft.Colors.AMBER_50
                    text_color = ft.Colors.AMBER_800
                    border_color = ft.Colors.AMBER_200
                else:
                    status = attendance.get(d, "")
                    if status == "присутствовал":
                        bg_color = ft.Colors.GREEN_100
                        text_color = ft.Colors.GREEN_800
                        border_color = ft.Colors.GREEN_300
                    elif status == "отсутствовал":
                        bg_color = ft.Colors.RED_100
                        text_color = ft.Colors.RED_800
                        border_color = ft.Colors.RED_300
                    else:
                        bg_color = ft.Colors.GREY_50
                        text_color = ft.Colors.GREY_700
                        border_color = ft.Colors.GREY_300

                def toggle_status(e, day=d):
                    if day.month != self.current_month or day.weekday() >= 5:
                        return

                    current_child_name = self.current_child
                    service_id_val = int(self.current_service_id)
                    old_status = attendance.get(day, "")

                    if old_status == "":
                        new_status = "присутствовал"
                    elif old_status == "присутствовал":
                        new_status = "отсутствовал"
                    else:
                        new_status = ""

                    self.current_attendance_status = new_status
                    self.current_selected_date = day

                    if new_status == "":
                        self.db.delete_attendance(current_child_name, service_id_val, day.isoformat())
                    else:
                        self.db.mark_attendance(
                            current_child_name,
                            service_id_val,
                            day.isoformat(),
                            new_status,
                            "",
                            self.user[6]
                        )

                    self.refresh_calendar()

                day_container = ft.Container(
                    content=ft.Text(
                        str(d.day),
                        size=16,
                        weight="bold",
                        color=text_color
                    ),
                    width=40,
                    height=40,
                    bgcolor=bg_color,
                    border=ft.Border.all(1, border_color),
                    border_radius=6,
                    alignment=ft.Alignment.CENTER,
                    padding=5,
                    on_click=toggle_status if d.month == selected_month and d.weekday() < 5 else None
                )

                week_row.append(day_container)

            self.calendar_container.controls.append(
                ft.Row(week_row, spacing=2, alignment=ft.MainAxisAlignment.CENTER)
            )
            self.calendar_container.controls.append(ft.Divider(height=2, color=ft.Colors.TRANSPARENT))

        legend_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    width=20,
                                    height=20,
                                    bgcolor=ft.Colors.GREEN_100,
                                    border=ft.Border.all(1, ft.Colors.GREEN_300),
                                    border_radius=4
                                ),
                                ft.Text("Присут.", size=10, color=ft.Colors.GREEN_800)
                            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=5
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    width=20,
                                    height=20,
                                    bgcolor=ft.Colors.RED_100,
                                    border=ft.Border.all(1, ft.Colors.RED_300),
                                    border_radius=4
                                ),
                                ft.Text("Отсут.", size=10, color=ft.Colors.RED_800)
                            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=5
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    width=20,
                                    height=20,
                                    bgcolor=ft.Colors.AMBER_50,
                                    border=ft.Border.all(1, ft.Colors.AMBER_200),
                                    border_radius=4
                                ),
                                ft.Text("Выходной", size=10, color=ft.Colors.AMBER_800)
                            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=5
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    width=20,
                                    height=20,
                                    bgcolor=ft.Colors.GREY_50,
                                    border=ft.Border.all(1, ft.Colors.GREY_300),
                                    border_radius=4
                                ),
                                ft.Text("Не отм.", size=10, color=ft.Colors.GREY_700)
                            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=5
                        ),
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True
                ),
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        legend_container = ft.Container(
            content=legend_content,
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_50,
            margin=ft.margin.only(top=10),
            alignment=ft.Alignment.CENTER,
            width=580
        )

        self.calendar_container.controls.append(legend_container)
        self.calendar_container.update()

    def mark_all_children(self):
        try:
            if self.current_selected_date is None or self.current_attendance_status is None:
                self.show_message("Сначала выберите дату и отметьте одного ребенка!", ft.Colors.RED)
                return

            if not self.current_service_id:
                self.show_message("Выберите кружок", ft.Colors.RED)
                return

            result = self.db.mark_all_children_for_service_date(
                int(self.current_service_id),
                self.current_selected_date.isoformat(),
                self.current_attendance_status
            )

            count = result.get("count", 0)

            self.show_message(
                f"✅ Отмечено {count} детей как '{self.current_attendance_status or 'сброшено'}'",
                ft.Colors.GREEN
            )

            self.refresh_calendar()

        except Exception as e:
            self.show_message(f"Ошибка: {str(e)}", ft.Colors.RED)

    def reset_group_dates(self):
        try:
            if not self.current_selected_date:
                self.show_message("Сначала выберите дату!", ft.Colors.RED)
                return

            if not self.current_service_id:
                self.show_message("Выберите кружок", ft.Colors.RED)
                return

            result = self.db.reset_all_children_for_service_date(
                int(self.current_service_id),
                self.current_selected_date.isoformat()
            )

            count = result.get("count", 0)

            self.show_message(f"🔄 Удалено {count} отметок", ft.Colors.BLUE)
            self.refresh_calendar()

        except Exception as e:
            self.show_message(f"Ошибка: {str(e)}", ft.Colors.RED)

    def show_message(self, message, color):
        try:
            snackbar = ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=color,
                duration=3000,
                behavior=ft.SnackBarBehavior.FLOATING
            )
            if hasattr(self.page, "overlay"):
                if snackbar not in self.page.overlay:
                    self.page.overlay.append(snackbar)
            else:
                self.page.snack_bar = snackbar
            snackbar.open = True
            self.page.update()
        except Exception as e:
            print(f"Ошибка при показе сообщения: {e}")

    def logout(self):
        from main import logout_user
        logout_user(self.page, self.db)