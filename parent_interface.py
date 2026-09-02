import flet as ft
from datetime import datetime
import calendar
import platform
import subprocess
from urllib.parse import quote

class ParentInterface:
    def __init__(self, page, user, db):
        self.page = page
        self.user = user
        self.db = db

        self.current_child = user[5] if len(user) > 5 else None
        self.children = []

    # =========================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================
    def only_digits(self, value, max_len=None):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if max_len:
            digits = digits[:max_len]
        return digits
    def normalize_year_value(self, value):
        """
        Ограничивает год календаря.
        Можно выбирать только от 2025 до 2200.
        """
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
                # Если пришло из БД: 20230415 -> 15.04.2023
                try:
                    dt = datetime.strptime(
                        f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}",
                        "%Y-%m-%d"
                    )
                    return dt.strftime("%d.%m.%Y")
                except Exception:
                    pass

                # Если уже было введено как 15042023 -> 15.04.2023
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
                if 11 <= n % 100 <= 14:
                    return "лет"
                if n % 10 == 1:
                    return "год"
                if 2 <= n % 10 <= 4:
                    return "года"
                return "лет"

            def month_word(n):
                if 11 <= n % 100 <= 14:
                    return "месяцев"
                if n % 10 == 1:
                    return "месяц"
                if 2 <= n % 10 <= 4:
                    return "месяца"
                return "месяцев"

            if years <= 0:
                return f"{months} {month_word(months)}"

            if months <= 0:
                return f"{years} {year_word(years)}"

            return f"{years} {year_word(years)} {months} {month_word(months)}"

        except Exception:
            return "-"

    def normalize_child(self, child):
        """
        Ожидаемый формат из get_children_by_parent:
        child_name, group_name, parent_phone, child_birthdate, child_age

        Но если БД возвращает только:
        child_name, group_name

        то метод безопасно дополнит пустыми значениями.
        """
        child = list(child)

        while len(child) < 5:
            child.append("")

        return child[:5]

    def get_current_child_data(self):
        self.children = self.db.get_children_by_parent(self.user[4]) or []

        for child in self.children:
            child_name, group_name, parent_phone, child_birthdate, child_age = self.normalize_child(child)

            if child_name == self.current_child:
                return {
                    "child_name": child_name,
                    "group_name": group_name or "-",
                    "parent_phone": parent_phone or self.get_parent_phone_from_user(),
                    "birthdate": child_birthdate or "-",
                    "age": child_age or self.calculate_age_text(child_birthdate),
                }

        if self.children:
            child_name, group_name, parent_phone, child_birthdate, child_age = self.normalize_child(self.children[0])
            self.current_child = child_name

            return {
                "child_name": child_name,
                "group_name": group_name or "-",
                "parent_phone": parent_phone or self.get_parent_phone_from_user(),
                "birthdate": child_birthdate or "-",
                "age": child_age or self.calculate_age_text(child_birthdate),
            }

        return None

    def get_parent_phone_from_user(self):
        try:
            if len(self.user) > 7 and self.user[7]:
                return self.user[7]
            return ""
        except Exception:
            return ""

    def get_child_services_safe(self, child_name):
        try:
            return self.db.get_child_services(child_name) or []
        except Exception as e:
            print(f"Ошибка get_child_services: {e}")
            return []



    def show_child_info_dialog(self, child_name=None):
        if not child_name:
            child_name = self.current_child

        if not child_name:
            self.show_message("Ребенок не выбран", ft.Colors.RED)
            return

        self.children = self.db.get_children_by_parent(self.user[4]) or []

        child_data = None
        for child in self.children:
            ch_name, group_name, parent_phone, child_birthdate, child_age = self.normalize_child(child)
            if ch_name == child_name:
                child_data = {
                    "child_name": ch_name,
                    "group_name": group_name or "-",
                    "parent_phone": parent_phone or self.get_parent_phone_from_user(),
                    "birthdate": child_birthdate or "-",
                    "age": child_age or self.calculate_age_text(child_birthdate),
                }
                break

        if not child_data:
            self.show_message("Не удалось найти данные ребенка", ft.Colors.RED)
            return

        services = self.get_child_services_safe(child_name)

        if services:
            service_lines = []
            for service in services:
                try:
                    service_lines.append(f"• {service[1]}")
                except Exception:
                    service_lines.append(f"• {service}")
            services_text = "\n".join(service_lines)
        else:
            services_text = "Не записан на кружки"

        parent_phone = self.format_phone_value(child_data.get("parent_phone"))

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
            title=ft.Text("Информация о ребенке", weight="bold"),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    [
                        ft.Text("Ребенок", size=16, weight="bold", color=ft.Colors.BLUE_800),
                        ft.Text(f"Имя: {child_data.get('child_name') or '-'}", size=14, selectable=True),
                        ft.Text(f"Группа: {child_data.get('group_name') or '-'}", size=14, selectable=True),
                        ft.Text(
                            f"Дата рождения: {self.format_birthdate_for_view(child_data.get('birthdate'))}",
                            size=14,
                            selectable=True
                        ),
                        ft.Text(f"Возраст: {child_data.get('age') or '-'}", size=14, selectable=True),

                        ft.Divider(height=20),

                        ft.Text("Родитель", size=16, weight="bold", color=ft.Colors.GREEN_800),
                        ft.Text(f"ФИО родителя: {self.user[4] or '-'}", size=14, selectable=True),
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
        self.page.title = f"{self.user[4]}"
        self.page.bgcolor = "#EEF3F8"

        self.children = self.db.get_children_by_parent(self.user[4]) or []

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

        if not self.children:
            content = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Ошибка: у вас нет привязанных детей",
                            size=20,
                            color=ft.Colors.RED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment(0, 0),
                expand=True,
            )

            self.page.add(
                ft.Container(
                    content=ft.Column(
                        [
                            top_bar,
                            content,
                        ],
                        expand=True,
                    ),
                    bgcolor="#EEF3F8",
                    padding=20,
                    expand=True,
                )
            )
            self.page.update()
            return

        child_names = [self.normalize_child(child)[0] for child in self.children]

        if self.current_child not in child_names:
            self.current_child = child_names[0]

        current_child_data = self.get_current_child_data()

        current_group = current_child_data.get("group_name", "-") if current_child_data else "-"
        current_birthdate = current_child_data.get("birthdate", "-") if current_child_data else "-"
        current_age = current_child_data.get("age", "-") if current_child_data else "-"
        parent_phone = self.format_phone_value(
            current_child_data.get("parent_phone", "") if current_child_data else self.get_parent_phone_from_user()
        )

        child_selector = ft.Dropdown(
            label="Выберите ребенка",
            options=[ft.dropdown.Option(child_name) for child_name in child_names],
            value=self.current_child,
            width=320,
            border_radius=10,
        )
        child_selector.on_change = lambda e: self.select_child(e.control.value)



        user_info = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"{self.user[4]}",
                        size=18,
                        weight="bold",
                        text_align=ft.TextAlign.CENTER,
                    ),

                    child_selector,
                    ft.Text(
                        f"Группа: {current_group}",
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Text(
                        f"Дата рождения: {self.format_birthdate_for_view(current_birthdate)}",
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Text(
                        f"Возраст: {current_age}",
                        size=13,
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
            width=430,
        )



        attendance_button = ft.ElevatedButton(
            "📅 Посещаемость детей",
            on_click=lambda e: self.show_attendance_calendar(),
            width=300,
            height=52,
        )

        payment_button = ft.ElevatedButton(
            "💳 Услуги и оплата",
            on_click=lambda e: self.show_services_payment(),
            width=300,
            height=52,
        )

        menu = ft.Container(
            content=ft.Column(
                [
                    user_info,
                    attendance_button,
                    payment_button,
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

    def select_child(self, child_name):
        self.current_child = child_name
        self.show_interface()

    # =========================
    # КАЛЕНДАРЬ ПОСЕЩАЕМОСТИ
    # =========================
    def show_attendance_calendar(self):
        self.page.clean()
        self.page.title = f"Посещаемость: {self.current_child}"
        self.page.bgcolor = "#EEF3F8"

        screen_width = self.page.width

        if not screen_width or screen_width <= 0:
            screen_width = 320

        page_padding = 8
        calendar_padding = 4
        row_spacing = 1

        calendar_width = screen_width - page_padding * 2

        if calendar_width > 520:
            calendar_width = 520

        if calendar_width < 220:
            calendar_width = 220

        inner_calendar_width = calendar_width - calendar_padding * 2

        available_width = inner_calendar_width - row_spacing * 6

        cell_size = int(available_width / 7)

        if cell_size > 44:
            cell_size = 44

        if cell_size < 22:
            cell_size = 22

        self.children = self.db.get_children_by_parent(self.user[4]) or []
        child_names = [self.normalize_child(child)[0] for child in self.children]

        if not child_names:
            self.show_message("У вас нет детей", ft.Colors.RED)
            self.show_interface()
            return

        if self.current_child not in child_names:
            self.current_child = child_names[0]

        child_dropdown = ft.Dropdown(
            label="Выберите ребенка",
            options=[ft.dropdown.Option(child_name) for child_name in child_names],
            width=calendar_width,
            value=self.current_child,
        )

        months = [
            ("Январь", 1), ("Февраль", 2), ("Март", 3), ("Апрель", 4),
            ("Май", 5), ("Июнь", 6), ("Июль", 7), ("Август", 8),
            ("Сентябрь", 9), ("Октябрь", 10), ("Ноябрь", 11), ("Декабрь", 12),
        ]

        current_month = datetime.now().month
        current_month_name = months[current_month - 1][0]

        month_field = ft.Dropdown(
            label="Месяц",
            options=[
                ft.dropdown.Option(
                    key=f"{name} ({num})",
                    text=f"{name} ({num})"
                )
                for name, num in months
            ],
            width=calendar_width,
            value=f"{current_month_name} ({current_month})",
        )

        year_field = self.setup_year_field(ft.TextField(
            label="Год",
            value=str(datetime.now().year),
            width=calendar_width,
            keyboard_type=ft.KeyboardType.NUMBER,
        ))

        initial_services = self.get_child_services_safe(self.current_child)

        service_dropdown = ft.Dropdown(
            label="Услуга",
            options=[ft.dropdown.Option(key=str(s[0]), text=s[1]) for s in initial_services],
            width=calendar_width,
            value=str(initial_services[0][0]) if initial_services else None,
        )

        calendar_container = ft.Column()

        def render_no_services(selected_child):
            calendar_container.controls.clear()
            calendar_container.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"У ребенка {selected_child} нет записей на услуги.",
                                size=16,
                                weight="bold",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Divider(height=10),
                            ft.Text(
                                "Запись на услуги выполняет администратор ДОУ.",
                                size=14,
                                color=ft.Colors.GREY_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=20,
                )
            )
            calendar_container.update()

        def add_legend():
            legend_content = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Container(
                                            width=20,
                                            height=20,
                                            bgcolor=ft.Colors.GREEN_100,
                                            border=ft.Border.all(1, ft.Colors.GREEN_300),
                                            border_radius=4,
                                        ),
                                        ft.Text("Присут.", size=10, color=ft.Colors.GREEN_800),
                                    ],
                                    spacing=2,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=5,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Container(
                                            width=20,
                                            height=20,
                                            bgcolor=ft.Colors.RED_100,
                                            border=ft.Border.all(1, ft.Colors.RED_300),
                                            border_radius=4,
                                        ),
                                        ft.Text("Отсут.", size=10, color=ft.Colors.RED_800),
                                    ],
                                    spacing=2,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=5,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Container(
                                            width=20,
                                            height=20,
                                            bgcolor=ft.Colors.AMBER_50,
                                            border=ft.Border.all(1, ft.Colors.AMBER_200),
                                            border_radius=4,
                                        ),
                                        ft.Text("Выходной", size=10, color=ft.Colors.AMBER_800),
                                    ],
                                    spacing=2,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=5,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Container(
                                            width=20,
                                            height=20,
                                            bgcolor=ft.Colors.GREY_50,
                                            border=ft.Border.all(1, ft.Colors.GREY_300),
                                            border_radius=4,
                                        ),
                                        ft.Text("Не отм.", size=10, color=ft.Colors.GREY_700),
                                    ],
                                    spacing=2,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=5,
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True,
                    ),
                ],
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

            legend_container = ft.Container(
                content=legend_content,
                padding=8,
                border=ft.Border.all(1, ft.Colors.GREY_200),
                border_radius=8,
                bgcolor=ft.Colors.BLUE_GREY_50,
                margin=ft.margin.only(top=10),
                alignment=ft.Alignment.CENTER,
                width=inner_calendar_width,
            )
            calendar_container.controls.append(legend_container)

        def load_services_for_child(selected_child):
            child_services = self.get_child_services_safe(selected_child)

            service_dropdown.options = [
                ft.dropdown.Option(key=str(s[0]), text=s[1])
                for s in child_services
            ]

            if child_services:
                service_dropdown.value = str(child_services[0][0])
            else:
                service_dropdown.value = None

            service_dropdown.update()

        def refresh_calendar():
            child_name = self.current_child
            service_id = service_dropdown.value

            if not child_name:
                return

            if not service_id:
                render_no_services(child_name)
                return

            try:
                selected_month = int(month_field.value.split("(")[-1].strip(")"))
            except Exception:
                selected_month = current_month

            year_text = str(year_field.value or "").strip()

            if len(year_text) == 4:
                selected_year = self.normalize_year_value(year_text)
                year_field.value = str(selected_year)
            else:
                selected_year = datetime.now().year

            first_day = f"{selected_year}-{selected_month:02d}-01"
            last_day_num = calendar.monthrange(selected_year, selected_month)[1]
            last_day = f"{selected_year}-{selected_month:02d}-{last_day_num:02d}"

            rows = self.db.get_attendance_for_child_service_month(
                child_name,
                int(service_id),
                first_day,
                last_day,
            ) or []

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

            calendar_container.controls.clear()

            month_names = [
                "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
            ]
            month_name = month_names[selected_month - 1]

            calendar_container.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"{month_name} {selected_year} — {child_name}",
                        size=18,
                        weight="bold",
                        color=ft.Colors.BLUE_800,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.padding.only(bottom=10),
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
                            color=ft.Colors.BLUE_GREY_700,
                        ),
                        width=cell_size,
                        height=cell_size - 8,
                        alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(0.5, ft.Colors.GREY_300),
                    )
                )

            calendar_container.controls.append(
                ft.Row(day_header_row, spacing=0, alignment=ft.MainAxisAlignment.CENTER)
            )
            calendar_container.controls.append(ft.Divider(height=5, color=ft.Colors.TRANSPARENT))

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

                    day_container = ft.Container(
                        content=ft.Text(
                            str(d.day),
                            size=11 if cell_size < 26 else 13 if cell_size < 34 else 15,
                            weight="bold",
                            color=text_color,
                        ),
                        width=cell_size,
                        height=cell_size,
                        bgcolor=bg_color,
                        border=ft.Border.all(1, border_color),
                        border_radius=6,
                        alignment=ft.Alignment.CENTER,
                        padding=2,
                    )

                    week_row.append(day_container)

                calendar_container.controls.append(
                    ft.Row(week_row, spacing=row_spacing, alignment=ft.MainAxisAlignment.CENTER)
                )
                calendar_container.controls.append(ft.Divider(height=2, color=ft.Colors.TRANSPARENT))

            add_legend()
            calendar_container.update()

        def on_child_changed(e):
            selected_child = None

            if hasattr(e, "data") and e.data:
                selected_child = str(e.data)
            elif e.control and e.control.value:
                selected_child = str(e.control.value)

            print("PARENT ON_CHILD_CHANGED ->", selected_child)

            if not selected_child:
                return

            self.current_child = selected_child

            child_dropdown.value = selected_child
            child_dropdown.update()

            load_services_for_child(self.current_child)
            refresh_calendar()
            self.page.update()

        def on_service_changed(e):
            selected_service_id = None

            if hasattr(e, "data") and e.data:
                selected_service_id = str(e.data)
            elif e.control and e.control.value:
                selected_service_id = str(e.control.value)

            print("PARENT ON_SERVICE_CHANGED ->", selected_service_id)

            if not selected_service_id:
                return

            service_dropdown.value = selected_service_id
            service_dropdown.update()

            refresh_calendar()
            self.page.update()

        def on_month_changed(e):
            selected_month = None

            if hasattr(e, "data") and e.data:
                selected_month = str(e.data)
            elif e.control and e.control.value:
                selected_month = str(e.control.value)

            print("PARENT ON_MONTH_CHANGED ->", selected_month)

            if selected_month:
                month_field.value = selected_month
                month_field.update()

            refresh_calendar()
            self.page.update()

        def on_year_changed(e):
            year_text = str(year_field.value or "").strip()

            # Пока пользователь не ввел 4 цифры, календарь не обновляем
            if len(year_text) < 4:
                return

            selected_year = self.normalize_year_value(year_text)

            if str(selected_year) != year_text:
                year_field.value = str(selected_year)
                year_field.update()

            refresh_calendar()
            self.page.update()

        child_dropdown.on_select = on_child_changed
        service_dropdown.on_select = on_service_changed
        month_field.on_select = on_month_changed
        year_field.on_change = on_year_changed



        back_button = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK,
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Календарь посещаемости", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                        ft.Column(
                            [child_dropdown, service_dropdown, month_field, year_field],
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=20),
                        ft.Container(
                            content=calendar_container,
                            width=calendar_width,
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=12,
                            padding=calendar_padding,
                            bgcolor=ft.Colors.WHITE,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Divider(height=20),
                        ft.Container(content=back_button, alignment=ft.Alignment.CENTER),
                    ],
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15,
                ),
                alignment=ft.Alignment.CENTER,
                padding=page_padding,
                expand=True,
            )
        )

        refresh_calendar()
        self.page.update()

    # =========================
    # УСЛУГИ И ОПЛАТА
    # =========================
    def show_payment_qr_dialog(self, child_name, amount):
        try:
            if amount is None:
                amount = 0

            try:
                amount = float(amount)
            except Exception:
                amount = 0

            amount_text = f"{amount:g} руб."

            qr_text = (
                f"Оплата прошла успешно\n"
                f"Ребенок: {child_name}\n"
                f"Сумма: {amount_text}"
            )

            qr_data = quote(qr_text)

            qr_url = (
                "https://api.qrserver.com/v1/create-qr-code/"
                f"?size=260x260&data={qr_data}"
            )

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Оплата услуги", weight="bold"),
                content=ft.Container(
                    width=360,
                    content=ft.Column(
                        [
                            ft.Text(
                                f"К оплате: {amount_text}",
                                size=16,
                                weight="bold",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Отсканируйте QR-код для оплаты",
                                size=14,
                                color=ft.Colors.GREY_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Container(
                                content=ft.Image(
                                    src=qr_url,
                                    width=260,
                                    height=260,
                                ),
                                alignment=ft.Alignment.CENTER,
                                padding=10,
                                bgcolor=ft.Colors.WHITE,
                                border=ft.Border.all(1, ft.Colors.GREY_300),
                                border_radius=12,
                            ),
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "Закрыть",
                        on_click=lambda e: self.close_dialog(dialog)
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            self.open_dialog(dialog)

        except Exception as e:
            print(f"Ошибка показа QR-кода оплаты: {e}")
            self.show_message(f"Ошибка QR: {e}", ft.Colors.RED)


    def show_services_payment(self):
        self.page.clean()
        self.page.title = "Услуги и оплата"
        self.page.bgcolor = "#EEF3F8"




        self.children = self.db.get_children_by_parent(self.user[4]) or []
        child_names = [self.normalize_child(child)[0] for child in self.children]

        if not child_names:
            self.show_message("У вас нет детей", ft.Colors.RED)
            self.show_interface()
            return

        if self.current_child not in child_names:
            self.current_child = child_names[0]

        child_dropdown = ft.Dropdown(
            label="Выберите ребенка",
            options=[ft.dropdown.Option(key=child_name, text=child_name) for child_name in child_names],
            width=300,
            value=self.current_child,
        )

        services_container = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8)

        child_total_text = ft.Text(
            f"Начислено за {self.current_child}: 0 руб.",
            size=16,
            weight="bold",
            text_align=ft.TextAlign.CENTER,
        )
        current_child_total = {"value": 0}

        all_children_total_text = ft.Text(
            "Всего начислено по всем детям: 0 руб.",
            size=14,
            color=ft.Colors.PURPLE,
            weight="bold",
            text_align=ft.TextAlign.CENTER,
        )
        pay_button = ft.ElevatedButton(
            "💳 Оплатить",
            icon=ft.Icons.PAYMENT,
            width=300,
            height=45,
            bgcolor=ft.Colors.GREEN_100,
            color=ft.Colors.GREEN,
            on_click=lambda e: self.show_payment_qr_dialog(
                self.current_child,
                current_child_total["value"]
            )
        )

        def show_child_services(selected_child):
            # Родитель видит только те услуги, на которые ребенок уже записан.
            # Самостоятельной записи здесь больше нет.
            services = self.get_child_services_safe(selected_child) or []

            service_controls = []
            child_total = 0

            attendance_data = self.db.get_attendance(child_name=selected_child) or []

            attendance_map = {}

            for rec in attendance_data:
                try:
                    rec_service_id = int(rec[2])
                    rec_date = rec[3]
                    status = rec[4]

                    if rec_service_id not in attendance_map:
                        attendance_map[rec_service_id] = {}

                    attendance_map[rec_service_id][rec_date] = status

                except Exception:
                    continue

            if not services:
                service_controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Ребенок пока не записан на дополнительные услуги.",
                                        size=16,
                                        weight="bold",
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                    ft.Text(
                                        "Запись на услуги выполняет администратор ДОУ.",
                                        size=13,
                                        color=ft.Colors.GREY_700,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=8,
                            ),
                            padding=20,
                            width=450,
                            alignment=ft.Alignment.CENTER,
                        )
                    )
                )

                return service_controls, child_total

            for service in services:
                try:
                    sid = int(service[0])
                    name = service[1]
                    desc = service[2]
                    price = service[3]
                    teacher = service[4]
                except Exception:
                    continue

                service_attendance = attendance_map.get(sid, {})

                count_present = sum(
                    1 for status in service_attendance.values()
                    if status == "присутствовал"
                )

                try:
                    cost = count_present * float(price)
                except Exception:
                    cost = 0

                child_total += cost

                service_controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        name,
                                        size=16,
                                        weight="bold",
                                        color=ft.Colors.BLUE,
                                    ),
                                    ft.Text(
                                        desc or "Нет описания",
                                        size=14,
                                    ),
                                    ft.Text(
                                        f"Воспитатель: {teacher or '-'}",
                                        size=12,
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Text(
                                        f"Цена за занятие: {price} руб.",
                                        size=12,
                                    ),
                                    ft.Text(
                                        f"Посещено занятий: {count_present}",
                                        size=12,
                                    ),
                                    ft.Text(
                                        f"Начислено: {cost:g} руб.",
                                        size=14,
                                        weight="bold",
                                        color=ft.Colors.GREEN,
                                    ),
                                ],
                                spacing=5,
                            ),
                            padding=12,
                            width=450,
                        )
                    )
                )

            return service_controls, child_total

        def refresh_services():
            child_name = self.current_child

            if not child_name:
                return

            services_controls, child_total = show_child_services(child_name)

            services_container.controls.clear()
            services_container.controls.extend(services_controls)

            child_total_text.value = f"Начислено за {child_name}: {child_total:g} руб."
            current_child_total["value"] = child_total

            total_all_children = 0

            for child in self.children:
                child_name_all = self.normalize_child(child)[0]

                child_services = self.get_child_services_safe(child_name_all)
                attendance_data = self.db.get_attendance(child_name=child_name_all) or []

                for service in child_services:
                    try:
                        service_id, _, _, price, _ = service

                        present_count = sum(
                            1 for rec in attendance_data
                            if rec[2] == service_id and rec[4] == "присутствовал"
                        )

                        total_all_children += present_count * float(price)
                    except Exception:
                        continue

            all_children_total_text.value = f"Всего начислено по всем детям: {total_all_children:g} руб."

            services_container.update()
            child_total_text.update()
            all_children_total_text.update()

        def on_child_changed(e):
            self.current_child = e.control.value
            refresh_services()

        child_dropdown.on_change = on_child_changed



        back_btn = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK,
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Услуги и оплата", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                        child_dropdown,
                        ft.Divider(height=12),
                        ft.Container(
                            content=services_container,
                            height=420,
                            width=500,
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=12,
                            padding=10,
                            bgcolor=ft.Colors.WHITE,
                        ),
                        ft.Divider(height=12),
                        child_total_text,
                        all_children_total_text,
                        pay_button,
                        ft.Divider(height=12),
                        back_btn,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                alignment=ft.Alignment.CENTER,
                padding=20,
                expand=True,
            )
        )

        refresh_services()
        self.page.update()



    # =========================
    # ОБЩИЕ МЕТОДЫ
    # =========================
    def show_message(self, message, color):
        try:
            snackbar = ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=color,
                duration=3000,
                behavior=ft.SnackBarBehavior.FLOATING,
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