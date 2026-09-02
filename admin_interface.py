import flet as ft
from datetime import datetime, timedelta
import csv
import tempfile
import os
import hashlib

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


class AdminInterface:
    def __init__(self, page, user, db):
        self.page = page
        self.user = user
        self.db = db

    # =========================
    # ОСНОВНОЕ МЕНЮ
    # =========================
    def show_interface(self):
        self.page.clean()
        self.page.title = f"{self.user[4]}"
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
                        f"{self.user[4]}",
                        size=18,
                        weight="bold",
                        text_align=ft.TextAlign.CENTER,
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

        services_button = ft.ElevatedButton(
            "Управление услугами",
            on_click=lambda e: self.show_services_management(),
            width=300,
            height=52,
        )

        users_button = ft.ElevatedButton(
            "Управление пользователями",
            on_click=lambda e: self.show_users_management(),
            width=300,
            height=52,
        )

        reports_button = ft.ElevatedButton(
            "📊 Экспорт отчетов",
            on_click=lambda e: self.show_reports_interface(),
            width=300,
            height=52,
            bgcolor=ft.Colors.GREEN_100,
            color=ft.Colors.GREEN,
        )

        menu = ft.Container(
            content=ft.Column(
                [
                    user_info,
                    services_button,
                    users_button,
                    reports_button,
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

    # =========================
    # УПРАВЛЕНИЕ УСЛУГАМИ
    # =========================
    def show_services_management(self):
        self.page.clean()
        self.page.title = "Управление услугами"

        services = self.db.get_services() or []
        teachers = self.db.get_all_teachers() or []
        teacher_names = [t[4] for t in teachers]

        name_field = ft.TextField(label="Название услуги", width=400)
        desc_field = ft.TextField(label="Описание", width=400, multiline=True, max_lines=3)
        price_field = ft.TextField(label="Стоимость (руб.)", width=400)

        teacher_dropdown = ft.Dropdown(
            label="Воспитатель",
            width=400,
            options=[ft.dropdown.Option(name) for name in teacher_names]
        )

        def add_service(e):
            if not (name_field.value and desc_field.value and price_field.value and teacher_dropdown.value):
                self.show_message("Заполните все поля", ft.Colors.RED)
                return

            try:
                price = float(price_field.value)
            except ValueError:
                self.show_message("Введите корректную стоимость", ft.Colors.RED)
                return

            success = self.db.add_service(
                name_field.value.strip(),
                desc_field.value.strip(),
                price,
                teacher_dropdown.value
            )

            if success:
                self.show_message("Услуга успешно добавлена", ft.Colors.GREEN)
                self.show_services_management()
            else:
                self.show_message("Ошибка при добавлении услуги", ft.Colors.RED)

        services_list = ft.Column(scroll=ft.ScrollMode.AUTO)

        for service in services:
            service_id, name, description, price, teacher = service

            def open_service_dialog(
                sid=service_id,
                sname=name,
                sdesc=description,
                sprice=price,
                steacher=teacher
            ):
                dialog = ft.AlertDialog(
                    title=ft.Text(f"Редактирование услуги: {sname}", weight="bold"),
                    modal=True
                )

                edit_name = ft.TextField(label="Название", value=sname or "", width=420)
                edit_desc = ft.TextField(label="Описание", value=sdesc or "", multiline=True, width=420)
                edit_price = ft.TextField(label="Стоимость", value=str(sprice or ""), width=420)
                edit_teacher = ft.Dropdown(
                    label="Воспитатель",
                    width=420,
                    options=[ft.dropdown.Option(t_name) for t_name in teacher_names],
                    value=steacher if steacher in teacher_names else None
                )

                def save_changes(e):
                    try:
                        new_name = (edit_name.value or "").strip()
                        new_desc = (edit_desc.value or "").strip()
                        new_price = float((edit_price.value or "").strip())
                        new_teacher = edit_teacher.value

                        if not (new_name and new_desc and new_teacher):
                            self.show_message("Заполните все поля", ft.Colors.RED)
                            return

                        success = self.db.update_service_full(
                            sid, new_name, new_desc, new_price, new_teacher
                        )

                        if success:
                            self.show_message("Услуга обновлена", ft.Colors.GREEN)
                            self.close_dialog(dialog)
                            self.show_services_management()
                        else:
                            self.show_message("Ошибка при обновлении услуги", ft.Colors.RED)

                    except ValueError:
                        self.show_message("Введите корректную стоимость", ft.Colors.RED)

                save_btn = ft.ElevatedButton("Сохранить", on_click=save_changes)
                close_btn = ft.TextButton("Закрыть", on_click=lambda e: self.close_dialog(dialog))

                dialog.content = ft.Column(
                    [edit_name, edit_desc, edit_price, edit_teacher],
                    tight=True
                )
                dialog.actions = [save_btn, close_btn]

                self.open_dialog(dialog)

            name_button = ft.TextButton(
                content=ft.Text(name, size=16, weight="bold", expand=True),
                on_click=lambda e, f=open_service_dialog: f()
            )

            delete_btn = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED,
                tooltip=f"Удалить услугу {name}",
                on_click=lambda e, s_id=service_id: self.delete_service(s_id)
            )

            services_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([name_button, delete_btn]),
                                ft.Text(f"{price} руб. • {teacher}", size=12),
                            ]
                        ),
                        padding=10,
                        width=500
                    )
                )
            )

        services_container = ft.Container(
            content=services_list,
            height=320,
            width=540,
            padding=10,
            alignment=ft.Alignment.CENTER
        )

        back_button = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Управление услугами", size=20, weight="bold"),
                        ft.Divider(height=20),
                        ft.Text("Добавить новую услугу:", size=16),
                        name_field,
                        desc_field,
                        price_field,
                        teacher_dropdown,
                        ft.ElevatedButton("Добавить услугу", on_click=add_service, width=400),
                        ft.Divider(height=20),
                        ft.Text("Список услуг:", size=16),
                        services_container,
                        ft.Divider(height=20),
                        back_button
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                alignment=ft.Alignment.CENTER,
                padding=20,
                expand=True
            )
        )
        self.page.update()

    # =========================
    # УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
    # =========================
    # =========================
    # УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
    # =========================
    def show_users_management(self):
        self.page.clean()
        self.page.title = "Управление пользователями"
        available_groups = self.get_unique_groups() or []

        def make_group_options(current_group=None):
            groups = list(available_groups)

            if current_group and current_group not in groups:
                groups.append(current_group)

            return [ft.dropdown.Option(g) for g in groups if g]

        # -------------------------
        # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
        # -------------------------
        def only_digits(value, max_len=None):
            digits = "".join(ch for ch in str(value or "") if ch.isdigit())
            if max_len:
                digits = digits[:max_len]
            return digits

        def format_phone_value(value):
            """
            88005553535 -> 8 800 555 35 35
            Максимум 11 цифр.
            """
            digits = only_digits(value, 11)

            if len(digits) <= 1:
                return digits
            if len(digits) <= 4:
                return f"{digits[:1]} {digits[1:]}"
            if len(digits) <= 7:
                return f"{digits[:1]} {digits[1:4]} {digits[4:]}"
            if len(digits) <= 9:
                return f"{digits[:1]} {digits[1:4]} {digits[4:7]} {digits[7:]}"
            return f"{digits[:1]} {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"

        def normalize_phone_value(value):
            """
            Возвращает телефон уже с пробелами.
            """
            return format_phone_value(value)

        def phone_digits(value):
            return only_digits(value, 11)

        def is_valid_phone(value):
            digits = phone_digits(value)
            return len(digits) == 11 and digits[0] in ("7", "8")

        def setup_phone_field(field):
            def update_counter():
                digits_count = len(phone_digits(field.value))
                field.helper_text = f"{digits_count}/11 цифр"

            update_counter()

            def on_phone_change(e):
                old_value = field.value or ""
                new_value = format_phone_value(old_value)

                if old_value != new_value:
                    field.value = new_value

                update_counter()
                self.page.update()

            field.on_change = on_phone_change
            return field

        def format_birthdate_input(value):
            """
            Вводим только цифры.
            Максимум 8 цифр.
            На экране показываем:
            12052020 -> 12.05.2020
            """
            digits = only_digits(value, 8)

            if len(digits) <= 2:
                return digits

            if len(digits) <= 4:
                return f"{digits[:2]}.{digits[2:]}"

            return f"{digits[:2]}.{digits[2:4]}.{digits[4:8]}"

        def setup_birthdate_field(field):
            def on_birthdate_change(e):
                old_value = field.value or ""
                new_value = format_birthdate_input(old_value)

                if old_value != new_value:
                    field.value = new_value
                    self.page.update()

            field.on_change = on_birthdate_change
            return field

        def birthdate_ui_to_api(value):
            """
            Из поля интерфейса:
            31.12.2020 / 31122020
            делает формат для БД:
            2020-12-31
            """
            if not value:
                return None

            text = str(value).strip()

            for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y.%m.%d"):
                try:
                    return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
                except Exception:
                    pass

            digits = only_digits(value, 8)

            if len(digits) != 8:
                return None

            # Основной новый формат: 31122020 -> 2020-12-31
            candidates = [
                f"{digits[4:8]}-{digits[2:4]}-{digits[:2]}",

                # Поддержка старого формата, если где-то вставили 20201231
                f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}",
            ]

            for api_date in candidates:
                try:
                    datetime.strptime(api_date, "%Y-%m-%d")
                    return api_date
                except Exception:
                    pass

            return None

        def birthdate_api_to_ui(value):
            """
            Из БД:
            2020-12-31
            делает:
            31.12.2020
            """
            if not value:
                return ""

            text = str(value).strip()

            for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y"):
                try:
                    return datetime.strptime(text, fmt).strftime("%d.%m.%Y")
                except Exception:
                    pass

            digits = only_digits(value, 8)

            if len(digits) != 8:
                return str(value)

            candidates = [
                f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}",
                f"{digits[4:8]}-{digits[2:4]}-{digits[:2]}",
            ]

            for api_date in candidates:
                try:
                    return datetime.strptime(api_date, "%Y-%m-%d").strftime("%d.%m.%Y")
                except Exception:
                    pass

            return str(value)

        def validate_date(date_text):
            return birthdate_ui_to_api(date_text) is not None

        def normalize_user(user):
            """
            Приводит пользователя к единому формату:
            id, username, password, user_type, full_name, child_name, group_name, parent_phone, child_birthdate
            """
            user = list(user)

            while len(user) < 9:
                user.append("")

            return user[:9]

        def normalize_child(child):
            """
            Приводит ребенка к формату:
            child_name, group_name, parent_phone, child_birthdate, child_age
            """
            child = list(child)

            while len(child) < 5:
                child.append("")

            return child[:5]

        def copy_to_clipboard(text):
            try:
                if not text:
                    self.show_message("Нечего копировать", ft.Colors.ORANGE)
                    return

                text = format_phone_value(text)

                # 1 вариант: новые версии Flet
                if hasattr(self.page, "set_clipboard"):
                    self.page.set_clipboard(text)
                    self.show_message("Номер телефона скопирован", ft.Colors.GREEN)
                    return

                # 2 вариант: Windows / macOS / Linux через системные команды
                import platform
                import subprocess

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

            except Exception as ex:
                print(f"Ошибка копирования: {ex}")
                self.show_message("Не удалось скопировать номер", ft.Colors.RED)


        def refresh_groups_by_age(e=None):
            try:
                result = self.db.update_children_groups_by_age()

                if result and result.get("success"):
                    updated = result.get("updated", 0)
                    skipped = result.get("skipped", 0)
                    self.show_message(
                        f"Группы обновлены. Обновлено: {updated}, пропущено: {skipped}",
                        ft.Colors.GREEN
                    )
                    load_users()
                else:
                    self.show_message("Ошибка при обновлении групп", ft.Colors.RED)

            except Exception as ex:
                print(f"Ошибка refresh_groups_by_age: {ex}")
                self.show_message(f"Ошибка: {ex}", ft.Colors.RED)

        # -------------------------
        # ДИАЛОГ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯ
        # -------------------------
        def show_create_user_dialog(e=None):
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Добавить пользователя", weight="bold")
            )
            error_text = ft.Text(
                "",
                color=ft.Colors.RED,
                size=13,
                weight="bold",
                visible=False
            )

            def show_dialog_error(message):
                error_text.value = message
                error_text.visible = True
                self.page.update()

            def clear_dialog_error():
                error_text.value = ""
                error_text.visible = False
                self.page.update()

            username_field = ft.TextField(label="Логин", width=420)
            password_field = ft.TextField(
                label="Пароль",
                width=420,
                password=True,
                can_reveal_password=True
            )
            full_name_field = ft.TextField(label="ФИО", width=420)

            user_type_dropdown = ft.Dropdown(
                label="Тип пользователя",
                width=420,
                options=[
                    ft.dropdown.Option(key="parent", text="Родитель"),
                    ft.dropdown.Option(key="teacher", text="Воспитатель"),
                ],
                value="parent"
            )

            teacher_group_field = ft.Dropdown(
                label="Группа воспитателя",
                width=420,
                options=make_group_options(),
                visible=False
            )

            parent_phone_field = setup_phone_field(ft.TextField(
                label="Телефон родителя",
                width=420,
                hint_text="8 800 555 35 35",
                visible=True,
                keyboard_type=ft.KeyboardType.NUMBER
            ))

            children_column = ft.Column(spacing=10, visible=True)
            child_forms = []

            def add_child_form(e=None):
                child_number = len(child_forms) + 1

                child_name_field = ft.TextField(
                    label=f"Имя ребенка {child_number}",
                    width=250
                )

                child_birthdate_field = setup_birthdate_field(ft.TextField(
                    label="Дата рождения",
                    width=150,
                    hint_text="ДД.ММ.ГГГГ",
                    keyboard_type=ft.KeyboardType.NUMBER
                ))

                child_row = ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )

                remove_button = ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED,
                    tooltip="Удалить ребенка"
                )

                def remove_child(ev):
                    if child_row in children_column.controls:
                        index = children_column.controls.index(child_row)
                        children_column.controls.pop(index)

                        if index < len(child_forms):
                            child_forms.pop(index)

                        for i, form in enumerate(child_forms):
                            form["name"].label = f"Имя ребенка {i + 1}"

                        self.page.update()

                remove_button.on_click = remove_child

                child_row.controls = [
                    child_name_field,
                    child_birthdate_field,
                    remove_button if child_number > 1 else ft.Container(width=40)
                ]

                child_forms.append({
                    "name": child_name_field,
                    "birthdate": child_birthdate_field,
                    "row": child_row
                })

                children_column.controls.append(child_row)
                self.page.update()

            def update_form_visibility(e=None):
                is_parent = user_type_dropdown.value == "parent"
                is_teacher = user_type_dropdown.value == "teacher"

                teacher_group_field.visible = is_teacher
                parent_phone_field.visible = is_parent
                children_column.visible = is_parent
                add_child_button.visible = is_parent

                if is_parent and not child_forms:
                    add_child_form()

                self.page.update()

            add_child_button = ft.ElevatedButton(
                "Добавить ребенка",
                icon=ft.Icons.ADD,
                width=420,
                on_click=add_child_form
            )

            user_type_dropdown.on_change = update_form_visibility

            def save_user(e):
                username = (username_field.value or "").strip()
                password = (password_field.value or "").strip()
                full_name = (full_name_field.value or "").strip()
                user_type = user_type_dropdown.value

                clear_dialog_error()

                if not username:
                    show_dialog_error("Введите логин пользователя")
                    return

                if not password:
                    show_dialog_error("Введите пароль пользователя")
                    return

                if not full_name:
                    show_dialog_error("Введите ФИО пользователя")
                    return


                if user_type == "teacher":
                    teacher_group = (teacher_group_field.value or "").strip()

                    if not teacher_group:
                        show_dialog_error("Для воспитателя укажите группу")
                        return

                    success = self.db.register_user(
                        username=username,
                        password=password,
                        user_type="teacher",
                        full_name=full_name,
                        child_name=None,
                        group_name=teacher_group,
                        parent_phone=None,
                        child_birthdate=None
                    )

                    if success:
                        self.show_message("Воспитатель успешно добавлен", ft.Colors.GREEN)
                        self.close_dialog(dialog)
                        self.show_users_management()
                    else:
                        show_dialog_error("Не удалось создать воспитателя. Возможно, такой логин уже существует")

                    return

                parent_phone = normalize_phone_value(parent_phone_field.value)

                if not parent_phone:
                    show_dialog_error("Для родителя укажите телефон")
                    return

                if not is_valid_phone(parent_phone):
                    show_dialog_error("Телефон должен содержать 11 цифр и начинаться с 7 или 8")
                    return

                valid_children = []

                for form in child_forms:
                    child_name = (form["name"].value or "").strip()
                    child_birthdate = (form["birthdate"].value or "").strip()

                    if not child_name and not child_birthdate:
                        continue

                    if not child_name:
                        show_dialog_error("Укажите имя ребенка")
                        return

                    if not child_birthdate:
                        show_dialog_error(f"Укажите дату рождения ребенка {child_name}")
                        return

                    child_birthdate_api = birthdate_ui_to_api(child_birthdate)

                    if not child_birthdate_api:
                        show_dialog_error(
                            f"Дата рождения ребенка {child_name} должна быть в формате ДД.ММ.ГГГГ, например 12.01.2026"
                        )
                        return

                    valid_children.append((child_name, child_birthdate_api))

                if not valid_children:
                    show_dialog_error("Для родителя нужно добавить хотя бы одного ребенка")
                    return

                first_child_name, first_child_birthdate = valid_children[0]

                success = self.db.register_user(
                    username=username,
                    password=password,
                    user_type="parent",
                    full_name=full_name,
                    child_name=first_child_name,
                    group_name=None,
                    parent_phone=parent_phone,
                    child_birthdate=first_child_birthdate
                )

                if not success:
                    show_dialog_error(
                        "Не удалось создать родителя. Возможные причины: логин уже занят, телефон не указан, возраст ребенка меньше 1 года 5 месяцев или больше 8 лет"
                    )
                    return

                if len(valid_children) > 1:
                    for child_name, child_birthdate in valid_children[1:]:
                        child_success = self.db.add_child_to_parent(
                            full_name,
                            child_name,
                            parent_phone,
                            child_birthdate
                        )

                        if not child_success:
                            show_dialog_error(
                                f"Родитель создан, но ребенка {child_name} добавить не удалось. Проверьте дату рождения"
                            )
                            return

                self.show_message("Родитель успешно добавлен", ft.Colors.GREEN)
                self.close_dialog(dialog)
                self.show_users_management()

            dialog.content = ft.Container(
                width=460,
                height=520,
                content=ft.Column(
                    [
                        error_text,
                        username_field,
                        password_field,
                        full_name_field,
                        user_type_dropdown,
                        teacher_group_field,
                        parent_phone_field,
                        ft.Text("Дети:", size=14, weight="bold", visible=True),
                        children_column,
                        add_child_button,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )

            dialog.actions = [
                ft.ElevatedButton("Создать", on_click=save_user),
                ft.TextButton("Отмена", on_click=lambda e: self.close_dialog(dialog))
            ]

            self.open_dialog(dialog)
            update_form_visibility()

        # -------------------------
        # ДИАЛОГ РЕДАКТИРОВАНИЯ ПОЛЬЗОВАТЕЛЯ
        # -------------------------
        def show_edit_user_dialog(user_id, username, password_hash, user_type, full_name, group_name):
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Редактирование пользователя: {full_name}", weight="bold")
            )

            username_field = ft.TextField(label="Логин", value=username or "", width=420)
            password_field = ft.TextField(
                label="Новый пароль (оставьте пустым, если не менять)",
                width=420,
                password=True,
                can_reveal_password=True
            )
            full_name_field = ft.TextField(label="ФИО", value=full_name or "", width=420)

            group_field = ft.Dropdown(
                label="Группа воспитателя",
                value=group_name if group_name in available_groups else group_name,
                width=420,
                options=make_group_options(group_name),
                visible=user_type == "teacher"
            )

            def save_user(e):
                new_username = (username_field.value or "").strip()
                new_password = (password_field.value or "").strip()
                new_full_name = (full_name_field.value or "").strip()

                if not new_username or not new_full_name:
                    self.show_message("Заполните логин и ФИО", ft.Colors.RED)
                    return

                final_password = password_hash
                if new_password:
                    final_password = hashlib.sha256(new_password.encode()).hexdigest()

                if user_type == "teacher":
                    new_group = (group_field.value or "").strip()

                    if not new_group:
                        self.show_message("Для воспитателя укажите группу", ft.Colors.RED)
                        return

                    success = self.db.update_user_full(
                        user_id,
                        new_username,
                        final_password,
                        "teacher",
                        new_full_name,
                        None,
                        new_group
                    )
                else:
                    success = self.db.update_user_full(
                        user_id,
                        new_username,
                        final_password,
                        "parent",
                        new_full_name,
                        None,
                        group_name
                    )

                if success:
                    self.show_message("Пользователь обновлен", ft.Colors.GREEN)
                    self.close_dialog(dialog)
                    self.show_users_management()
                else:
                    self.show_message("Ошибка при обновлении пользователя", ft.Colors.RED)

            dialog.content = ft.Container(
                width=460,
                content=ft.Column(
                    [
                        username_field,
                        password_field,
                        full_name_field,
                        group_field
                    ],
                    spacing=10,
                    tight=True
                )
            )

            dialog.actions = [
                ft.ElevatedButton("Сохранить", on_click=save_user),
                ft.TextButton("Отмена", on_click=lambda e: self.close_dialog(dialog))
            ]

            self.open_dialog(dialog)

        # -------------------------
        # ДИАЛОГ ДОБАВЛЕНИЯ РЕБЕНКА
        # -------------------------
        def show_add_child_dialog(parent_name, parent_phone_default=""):
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Добавить ребенка для {parent_name}", weight="bold")
            )

            child_name_field = ft.TextField(
                label="Имя ребенка",
                width=420
            )

            birthdate_field = setup_birthdate_field(ft.TextField(
                label="Дата рождения",
                hint_text="ДД.ММ.ГГГГ",
                width=420,
                keyboard_type=ft.KeyboardType.NUMBER
            ))

            phone_field = setup_phone_field(ft.TextField(
                label="Телефон родителя",
                value=normalize_phone_value(parent_phone_default),
                width=420,
                hint_text="8 800 555 35 35",
                keyboard_type=ft.KeyboardType.NUMBER
            ))

            copy_phone_button = ft.ElevatedButton(
                "Скопировать телефон",
                icon=ft.Icons.COPY,
                on_click=lambda e: copy_to_clipboard(phone_field.value),
                width=420
            )

            info_text = ft.Text(
                "Группа будет определена автоматически по дате рождения.",
                size=12,
                color=ft.Colors.GREY_700
            )

            def save_child(e):
                child_name = (child_name_field.value or "").strip()
                birthdate = (birthdate_field.value or "").strip()
                phone = normalize_phone_value(phone_field.value)

                if not is_valid_phone(phone):
                    self.show_message("Телефон должен содержать 11 цифр и начинаться с 7 или 8", ft.Colors.RED)
                    return

                if not child_name or not birthdate or not phone:
                    self.show_message("Заполните имя ребенка, дату рождения и телефон", ft.Colors.RED)
                    return

                birthdate_api = birthdate_ui_to_api(birthdate)

                if not birthdate_api:
                    self.show_message("Дата рождения должна быть в формате ДД.ММ.ГГГГ", ft.Colors.RED)
                    return

                success = self.db.add_child_to_parent(
                    parent_name,
                    child_name,
                    phone,
                    birthdate_api
                )

                if success:
                    self.show_message(f"Ребенок {child_name} добавлен", ft.Colors.GREEN)
                    self.close_dialog(dialog)
                    self.show_users_management()
                else:
                    self.show_message(
                        "Ошибка при добавлении ребенка. Проверьте возраст: от 1 года 5 месяцев до 8 лет",
                        ft.Colors.RED
                    )

            dialog.content = ft.Container(
                width=460,
                content=ft.Column(
                    [
                        child_name_field,
                        birthdate_field,
                        phone_field,
                        copy_phone_button,
                        info_text
                    ],
                    spacing=10,
                    tight=True
                )
            )

            dialog.actions = [
                ft.ElevatedButton("Добавить", on_click=save_child),
                ft.TextButton("Отмена", on_click=lambda e: self.close_dialog(dialog))
            ]

            self.open_dialog(dialog)

        # -------------------------
        # ДИАЛОГ РЕДАКТИРОВАНИЯ РЕБЕНКА
        # -------------------------
        def show_edit_child_dialog(parent_name, child_data):
            child_name, group_name, parent_phone, child_birthdate, child_age = normalize_child(child_data)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Редактирование ребенка: {child_name}", weight="bold")
            )

            child_name_field = ft.TextField(
                label="Имя ребенка",
                value=child_name or "",
                width=420
            )

            birthdate_field = setup_birthdate_field(ft.TextField(
                label="Дата рождения",
                value=birthdate_api_to_ui(child_birthdate),
                hint_text="ДД.ММ.ГГГГ",
                width=420,
                keyboard_type=ft.KeyboardType.NUMBER
            ))

            phone_field = setup_phone_field(ft.TextField(
                label="Телефон родителя",
                value=normalize_phone_value(parent_phone),
                width=420,
                hint_text="8 800 555 35 35",
                keyboard_type=ft.KeyboardType.NUMBER
            ))

            copy_phone_button = ft.ElevatedButton(
                "Скопировать телефон",
                icon=ft.Icons.COPY,
                on_click=lambda e: copy_to_clipboard(phone_field.value),
                width=420
            )

            current_info = ft.Text(
                f"Текущая группа: {group_name or '-'}\nТекущий возраст: {child_age or '-'}",
                size=12,
                color=ft.Colors.GREY_700
            )

            auto_info = ft.Text(
                "После сохранения группа ребенка будет пересчитана автоматически по дате рождения.",
                size=12,
                color=ft.Colors.BLUE_700
            )


            def update_child(e):
                new_child_name = (child_name_field.value or "").strip()
                new_birthdate = (birthdate_field.value or "").strip()
                new_phone = normalize_phone_value(phone_field.value)

                if not is_valid_phone(new_phone):
                    self.show_message("Телефон должен содержать 11 цифр и начинаться с 7 или 8", ft.Colors.RED)
                    return


                if not new_child_name or not new_birthdate or not new_phone:
                    self.show_message("Заполните имя ребенка, дату рождения и телефон", ft.Colors.RED)
                    return

                new_birthdate_api = birthdate_ui_to_api(new_birthdate)

                if not new_birthdate_api:
                    self.show_message("Дата рождения должна быть в формате ДД.ММ.ГГГГ", ft.Colors.RED)
                    return

                success = self.db.update_child(
                    parent_name,
                    child_name,
                    new_child_name,
                    new_phone,
                    new_birthdate_api
                )

                if success:
                    self.show_message(f"Ребенок {child_name} обновлен", ft.Colors.GREEN)
                    self.close_dialog(dialog)
                    self.show_users_management()
                else:
                    self.show_message(
                        "Ошибка при обновлении ребенка. Проверьте возраст: от 1 года 5 месяцев до 8 лет",
                        ft.Colors.RED
                    )

            def delete_child(e):
                confirm_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Подтверждение удаления"),
                    content=ft.Text(f"Удалить ребенка {child_name}?"),
                    actions=[
                        ft.TextButton(
                            "Да",
                            on_click=lambda ev: self.confirm_child_delete(
                                parent_name,
                                child_name,
                                confirm_dialog,
                                dialog
                            )
                        ),
                        ft.TextButton(
                            "Нет",
                            on_click=lambda ev: self.close_dialog(confirm_dialog)
                        )
                    ],
                    actions_alignment=ft.MainAxisAlignment.END
                )
                self.open_dialog(confirm_dialog)

            dialog.content = ft.Container(
                width=460,
                content=ft.Column(
                    [
                        child_name_field,
                        birthdate_field,
                        phone_field,
                        copy_phone_button,
                        current_info,
                        auto_info
                    ],
                    spacing=10,
                    tight=True
                )
            )

            dialog.actions = [
                ft.ElevatedButton("Сохранить", on_click=update_child),
                ft.ElevatedButton(
                    "Удалить",
                    on_click=delete_child,
                    bgcolor=ft.Colors.RED_100,
                    color=ft.Colors.RED
                ),
                ft.TextButton("Отмена", on_click=lambda e: self.close_dialog(dialog)),
            ]

            self.open_dialog(dialog)

        def show_child_services_dialog(child_name):
            """
            Диалог управления услугами конкретного ребенка.
            Администратор может записать ребенка на услугу или выписать его.
            """
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Услуги ребенка: {child_name}", weight="bold")
            )

            services_list = ft.Column(
                spacing=8,
                scroll=ft.ScrollMode.AUTO
            )

            info_text = ft.Text(
                "Администратор управляет записью ребенка на дополнительные услуги.",
                size=12,
                color=ft.Colors.GREY_700,
                text_align=ft.TextAlign.CENTER,
            )

            def to_int(value):
                try:
                    return int(value)
                except Exception:
                    return None

            def get_enrolled_ids():
                """
                Возвращает id услуг, на которые уже записан ребенок.
                """
                try:
                    ids = self.db.get_child_service_ids(child_name) or []
                    result = set()

                    for item in ids:
                        item_id = to_int(item)
                        if item_id is not None:
                            result.add(item_id)

                    return result

                except Exception as ex:
                    print(f"Ошибка получения услуг ребенка: {ex}")
                    return set()

            def refresh_services_list():
                services_list.controls.clear()

                try:
                    services = self.db.get_services() or []
                except Exception as ex:
                    print(f"Ошибка загрузки услуг: {ex}")
                    services = []

                enrolled_ids = get_enrolled_ids()

                if not services:
                    services_list.controls.append(
                        ft.Container(
                            content=ft.Text(
                                "Дополнительные услуги пока не добавлены.",
                                size=14,
                                color=ft.Colors.GREY_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            padding=15,
                            alignment=ft.Alignment.CENTER,
                        )
                    )
                    self.page.update()
                    return

                for service in services:
                    try:
                        service_id = to_int(service[0])
                        service_name = service[1] or "Без названия"
                        service_desc = service[2] or "Нет описания"
                        service_price = service[3]
                        teacher_name = service[4] or "-"
                    except Exception:
                        continue

                    if service_id is None:
                        continue

                    is_enrolled = service_id in enrolled_ids

                    status_text = ft.Text(
                        "Записан" if is_enrolled else "Не записан",
                        size=12,
                        weight="bold",
                        color=ft.Colors.GREEN if is_enrolled else ft.Colors.GREY_700,
                    )

                    if is_enrolled:
                        action_button = ft.ElevatedButton(
                            "Выписать",
                            width=120,
                            height=36,
                            bgcolor=ft.Colors.RED_100,
                            color=ft.Colors.RED,
                            on_click=lambda e, s_id=service_id, s_name=service_name: confirm_unenroll_service(s_id,
                                                                                                              s_name),
                        )
                    else:
                        action_button = ft.ElevatedButton(
                            "Записать",
                            width=120,
                            height=36,
                            bgcolor=ft.Colors.BLUE_100,
                            color=ft.Colors.BLUE,
                            on_click=lambda e, s_id=service_id, s_name=service_name: enroll_service(s_id, s_name),
                        )

                    services_list.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text(
                                                    service_name,
                                                    size=15,
                                                    weight="bold",
                                                    color=ft.Colors.BLUE_800,
                                                    expand=True,
                                                ),
                                                status_text,
                                            ],
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        ft.Text(
                                            service_desc,
                                            size=12,
                                            color=ft.Colors.GREY_800,
                                        ),
                                        ft.Text(
                                            f"Воспитатель: {teacher_name}",
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                        ft.Text(
                                            f"Стоимость: {service_price} руб.",
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                        ft.Row(
                                            [action_button],
                                            alignment=ft.MainAxisAlignment.END,
                                        ),
                                    ],
                                    spacing=5,
                                ),
                                padding=10,
                            )
                        )
                    )

                self.page.update()

            def enroll_service(service_id, service_name):
                try:
                    success = self.db.enroll_child_to_service(child_name, service_id)
                except Exception as ex:
                    print(f"Ошибка записи на услугу: {ex}")
                    success = False

                if success:
                    self.show_message(
                        f"Ребенок записан на услугу: {service_name}",
                        ft.Colors.GREEN
                    )
                    refresh_services_list()
                else:
                    self.show_message(
                        "Не удалось записать ребенка. Возможно, он уже записан на эту услугу.",
                        ft.Colors.ORANGE
                    )

            def confirm_unenroll_service(service_id, service_name):
                confirm_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Подтверждение"),
                    content=ft.Text(
                        f"Выписать ребенка {child_name} из услуги «{service_name}»?"
                    ),
                    actions=[
                        ft.TextButton(
                            "Отмена",
                            on_click=lambda e: self.close_dialog(confirm_dialog),
                        ),
                        ft.ElevatedButton(
                            "Выписать",
                            bgcolor=ft.Colors.RED_100,
                            color=ft.Colors.RED,
                            on_click=lambda e: unenroll_service(service_id, service_name, confirm_dialog),
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )

                self.open_dialog(confirm_dialog)

            def unenroll_service(service_id, service_name, confirm_dialog):
                self.close_dialog(confirm_dialog)

                try:
                    success = self.db.unenroll_child_from_service(child_name, service_id)
                except Exception as ex:
                    print(f"Ошибка выписки из услуги: {ex}")
                    success = False

                if success:
                    self.show_message(
                        f"Ребенок выписан из услуги: {service_name}",
                        ft.Colors.GREEN
                    )
                    refresh_services_list()
                else:
                    self.show_message(
                        "Не удалось выписать ребенка из услуги",
                        ft.Colors.RED
                    )

            dialog.content = ft.Container(
                width=460,
                height=520,
                content=ft.Column(
                    [
                        info_text,
                        ft.Divider(height=10),
                        services_list,
                    ],
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

            dialog.actions = [
                ft.TextButton(
                    "Закрыть",
                    on_click=lambda e: self.close_dialog(dialog)
                )
            ]

            self.open_dialog(dialog)
            refresh_services_list()



        # -------------------------
        # ФИЛЬТРЫ И СПИСОК
        # -------------------------
        search_field = ft.TextField(label="Поиск по ФИО", width=300)

        user_type_filter = ft.Dropdown(
            label="Тип пользователя",
            width=300,
            options=[
                ft.dropdown.Option("Все"),
                ft.dropdown.Option("Родитель"),
                ft.dropdown.Option("Воспитатель"),
            ],
            value="Все"
        )

        group_filter = ft.TextField(label="Поиск по группе", width=300)

        users_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8)

        def load_users(e=None):
            users_list.controls.clear()

            try:
                users = self.db.get_all_users_grouped() or []
            except Exception as ex:
                print(f"Ошибка загрузки пользователей: {ex}")
                self.show_message("Ошибка загрузки пользователей", ft.Colors.RED)
                return

            search_text = (search_field.value or "").lower().strip()
            type_value = user_type_filter.value
            group_text = (group_filter.value or "").lower().strip()

            for raw_user in users:
                user_id, username, password, user_type, full_name, child_name, group_name, parent_phone, child_birthdate = normalize_user(raw_user)

                if username == "admin":
                    continue

                user_type_text = "Родитель" if user_type == "parent" else "Воспитатель"

                if type_value != "Все":
                    if type_value == "Родитель" and user_type != "parent":
                        continue
                    if type_value == "Воспитатель" and user_type != "teacher":
                        continue

                if search_text and search_text not in (full_name or "").lower():
                    continue

                parent_children = []

                if user_type == "parent":
                    try:
                        parent_children = self.db.get_children_by_parent(full_name) or []
                    except Exception:
                        parent_children = []

                    if group_text:
                        found_group = False

                        for child in parent_children:
                            ch_name, ch_group, ch_phone, ch_birthdate, ch_age = normalize_child(child)
                            if group_text in (ch_group or "").lower():
                                found_group = True
                                break

                        if not found_group:
                            continue
                else:
                    if group_text and group_text not in (group_name or "").lower():
                        continue

                actual_user_id = user_id

                if not actual_user_id and user_type == "parent":
                    try:
                        actual_user_id = self.db.get_min_parent_user_id(full_name)
                    except Exception:
                        actual_user_id = None

                edit_user_button = ft.TextButton(
                    content=ft.Text(
                        f"{full_name} ({username})",
                        size=14,
                        weight="bold"
                    ),
                    on_click=lambda e,
                    u_id=actual_user_id,
                    uname=username,
                    pwd=password,
                    utype=user_type,
                    fname=full_name,
                    gname=group_name:
                    show_edit_user_dialog(u_id, uname, pwd, utype, fname, gname)
                )

                delete_btn = ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED,
                    tooltip=f"Удалить пользователя {full_name}",
                    on_click=lambda e, u_id=actual_user_id: self.delete_user(u_id)
                )

                right_buttons = [delete_btn]

                if user_type == "parent":
                    right_buttons.append(
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            icon_color=ft.Colors.BLUE,
                            tooltip=f"Добавить ребенка для {full_name}",
                            on_click=lambda e,
                            fname=full_name,
                            phone=parent_phone:
                            show_add_child_dialog(fname, phone)
                        )
                    )

                info_controls = [
                    edit_user_button,
                    ft.Text(f"Тип: {user_type_text}", size=12)
                ]

                if user_type == "teacher":
                    info_controls.append(
                        ft.Text(f"Группа: {group_name or '-'}", size=12)
                    )
                else:
                    phone_row = ft.Row(
                        [
                            ft.Text(f"Телефон: {format_phone_value(parent_phone) or '-'}", size=12),
                            ft.IconButton(
                                icon=ft.Icons.COPY,
                                icon_size=16,
                                tooltip="Скопировать телефон",
                                on_click=lambda e, phone=parent_phone: copy_to_clipboard(format_phone_value(phone))
                            )
                        ],
                        spacing=5,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    )

                    info_controls.append(phone_row)

                user_card_content = [
                    ft.Row(
                        [
                            ft.Column(info_controls, expand=True, spacing=3),
                            ft.Column(right_buttons, spacing=3)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                ]

                if user_type == "parent":
                    children_list = ft.Column(spacing=5)

                    if parent_children:
                        for child in parent_children:
                            ch_name, ch_group, ch_phone, ch_birthdate, ch_age = normalize_child(child)

                            child_text = (
                                f"• {ch_name} | {ch_group or '-'} | "
                                f"{ch_age or '-'} | дата рождения: {birthdate_api_to_ui(ch_birthdate) or '-'}"
                            )

                            child_row = ft.Row(
                                [
                                    ft.Text(
                                        child_text,
                                        size=12,
                                        color=ft.Colors.GREY_700,
                                        expand=True
                                    ),
                                    ft.Row(
                                        [
                                            ft.IconButton(
                                                icon=ft.Icons.LIST_ALT,
                                                icon_size=17,
                                                icon_color=ft.Colors.GREEN_600,
                                                tooltip=f"Услуги ребенка {ch_name}",
                                                on_click=lambda e,
                                                                c_name=ch_name:
                                                show_child_services_dialog(c_name)
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.EDIT,
                                                icon_size=16,
                                                icon_color=ft.Colors.BLUE_400,
                                                tooltip=f"Редактировать {ch_name}",
                                                on_click=lambda e,
                                                                pname=full_name,
                                                                cdata=child:
                                                show_edit_child_dialog(pname, cdata)
                                            ),
                                        ],
                                        spacing=0,
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            )


                            children_list.controls.append(child_row)
                    else:
                        children_list.controls.append(
                            ft.Text(
                                "Дети не найдены",
                                size=12,
                                color=ft.Colors.GREY_600
                            )
                        )

                    user_card_content.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "Дети:",
                                        size=12,
                                        weight="bold",
                                        color=ft.Colors.GREY_700
                                    ),
                                    children_list
                                ],
                                spacing=5
                            ),
                            padding=ft.padding.only(left=10, top=5)
                        )
                    )

                users_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(user_card_content, spacing=8),
                            padding=12,
                            width=760
                        )
                    )
                )

            self.page.update()

        # -------------------------
        # ВЕРХНЯЯ ПАНЕЛЬ
        # -------------------------
        add_user_button = ft.ElevatedButton(
            "Добавить пользователя",
            icon=ft.Icons.ADD,
            on_click=show_create_user_dialog,
            width=240,
            height=45
        )



        apply_filter_btn = ft.ElevatedButton(
            "Применить фильтры",
            on_click=load_users,
            width=300
        )

        filters_column = ft.Column(
            [
                ft.Text("Фильтры поиска:", size=16, weight="bold"),
                search_field,
                user_type_filter,
                group_filter,
                apply_filter_btn
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        back_button = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Управление пользователями",
                            size=22,
                            weight="bold",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Divider(height=15),
                        ft.Row(
                            [add_user_button],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=15
                        ),
                        ft.Divider(height=20),
                        ft.Container(
                            content=filters_column,
                            alignment=ft.Alignment.CENTER,
                            width=420
                        ),
                        ft.Divider(height=20),
                        ft.Text(
                            "Список пользователей:",
                            size=16,
                            weight="bold",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(
                            content=users_list,
                            height=460,
                            width=800,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                            border_radius=10,
                            padding=10
                        ),
                        ft.Divider(height=20),
                        back_button
                    ],
                    scroll=ft.ScrollMode.ADAPTIVE,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12
                ),
                alignment=ft.Alignment.CENTER,
                padding=20,
                expand=True
            )
        )

        load_users()
        self.page.update()

    def confirm_child_delete(self, parent_name, child_name, confirm_dialog, parent_dialog):
        try:
            self.close_dialog(confirm_dialog)
            success = self.db.delete_child(parent_name, child_name)
            if success:
                self.show_message(f"Ребенок {child_name} удален", ft.Colors.GREEN)
                self.close_dialog(parent_dialog)
                self.show_users_management()
            else:
                self.show_message("Ошибка при удалении ребенка", ft.Colors.RED)
        except Exception as e:
            print(f"Ошибка при удалении ребенка: {e}")
            self.show_message(f"Ошибка: {e}", ft.Colors.RED)

    # =========================
    # ОТЧЕТЫ
    # =========================
    def show_reports_interface(self):
        self.page.clean()
        self.page.title = "Экспорт отчетов"

        report_type_dropdown = ft.Dropdown(
            label="Тип отчета",
            width=300,
            options=[
                ft.dropdown.Option("attendance", "Посещаемость"),
                ft.dropdown.Option("payment", "Оплата"),
                ft.dropdown.Option("users", "Пользователи"),
                ft.dropdown.Option("services", "Услуги"),
            ],
            value="attendance"
        )

        period_dropdown = ft.Dropdown(
            label="Период",
            width=300,
            options=[
                ft.dropdown.Option("month", "Текущий месяц"),
                ft.dropdown.Option("last_month", "Прошлый месяц"),
                ft.dropdown.Option("quarter", "Квартал"),
                ft.dropdown.Option("year", "Год"),
            ],
            value="month"
        )

        group_filter = ft.Dropdown(
            label="Группа",
            width=300,
            options=[ft.dropdown.Option("Все группы")] + [
                ft.dropdown.Option(g) for g in self.get_unique_groups()
            ],
            value="Все группы"
        )

        excel_button = ft.ElevatedButton(
            "📊 Экспорт в Excel",
            on_click=lambda e: self.export_to_excel(
                report_type_dropdown.value,
                period_dropdown.value,
                group_filter.value
            ),
            width=250,
            height=50,
            bgcolor=ft.Colors.GREEN_100,
            color=ft.Colors.GREEN
        )

        pdf_button = ft.ElevatedButton(
            "📄 Экспорт в PDF",
            on_click=lambda e: self.export_to_pdf(
                report_type_dropdown.value,
                period_dropdown.value,
                group_filter.value
            ),
            width=250,
            height=50,
            bgcolor=ft.Colors.RED_100,
            color=ft.Colors.RED
        )

        back_button = ft.ElevatedButton(
            "Назад",
            on_click=lambda e: self.show_interface(),
            icon=ft.Icons.ARROW_BACK,
            width=250
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Экспорт отчетов", size=24, weight="bold", text_align=ft.TextAlign.CENTER),
                        ft.Divider(height=20),
                        ft.Column(
                            [report_type_dropdown, period_dropdown, group_filter],
                            spacing=15,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        ft.Divider(height=30),
                        ft.Column(
                            [excel_button, ft.Divider(height=10), pdf_button],
                            spacing=5,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        ft.Divider(height=30),
                        ft.Container(content=back_button, alignment=ft.Alignment.CENTER)
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15
                ),
                alignment=ft.Alignment.CENTER,
                padding=20,
                expand=True
            )
        )
        self.page.update()

    def get_unique_groups(self):
        try:
            return self.db.get_unique_groups()
        except Exception as e:
            print(f"Ошибка get_unique_groups: {e}")
            return []

    def get_date_range(self, period):
        today = datetime.now()

        def last_day_of_month(dt):
            if dt.month == 12:
                next_month = dt.replace(year=dt.year + 1, month=1, day=1)
            else:
                next_month = dt.replace(month=dt.month + 1, day=1)

            return next_month - timedelta(days=1)

        if period == "month":
            start_date = today.replace(day=1)
            end_date = last_day_of_month(today)

        elif period == "last_month":
            first_day_of_current_month = today.replace(day=1)
            end_date = first_day_of_current_month - timedelta(days=1)
            start_date = end_date.replace(day=1)

        elif period == "quarter":
            quarter = (today.month - 1) // 3
            start_month = quarter * 3 + 1

            start_date = today.replace(month=start_month, day=1)

            end_month = start_month + 2
            end_month_date = today.replace(month=end_month, day=1)
            end_date = last_day_of_month(end_month_date)

        elif period == "year":
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)

        else:
            start_date = today.replace(day=1)
            end_date = last_day_of_month(today)

        return start_date, end_date

    def export_to_excel(self, report_type, period, group_filter):
        try:
            start_date, end_date = self.get_date_range(period)

            if report_type == "attendance":
                data = self.get_attendance_data(start_date, end_date, group_filter)
                filename = f"посещаемость_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                self.save_csv_attendance(data, filename)

            elif report_type == "payment":
                data = self.get_payment_data(start_date, end_date, group_filter)
                filename = f"оплата_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                self.save_csv_payment(data, filename)

            elif report_type == "users":
                data = self.get_users_data()
                filename = "пользователи.csv"
                self.save_csv_users(data, filename)

            elif report_type == "services":
                data = self.get_services_data()
                filename = "услуги.csv"
                self.save_csv_services(data, filename)

        except Exception as e:
            self.show_message(f"Ошибка экспорта: {str(e)}", ft.Colors.RED)

    def export_to_pdf(self, report_type, period, group_filter):
        try:
            if not HAS_PDF:
                self.show_message("Установите библиотеку: pip install reportlab", ft.Colors.ORANGE)
                return

            start_date, end_date = self.get_date_range(period)

            if report_type == "attendance":
                data = self.get_attendance_data(start_date, end_date, group_filter)
                filename = f"посещаемость_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
                self.create_pdf_attendance(data, filename, start_date, end_date, group_filter)

            elif report_type == "payment":
                data = self.get_payment_data(start_date, end_date, group_filter)
                filename = f"оплата_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
                self.create_pdf_payment(data, filename, start_date, end_date, group_filter)

            elif report_type == "users":
                data = self.get_users_data()
                filename = "пользователи.pdf"
                self.create_pdf_users(data, filename)

            elif report_type == "services":
                data = self.get_services_data()
                filename = "услуги.pdf"
                self.create_pdf_services(data, filename)

            else:
                self.show_message("Неизвестный тип отчета", ft.Colors.RED)

        except Exception as e:
            self.show_message(f"Ошибка PDF экспорта: {str(e)}", ft.Colors.RED)

    def format_date_for_view(self, value):
        try:
            if not value:
                return ""

            text = str(value).strip()

            for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y"):
                try:
                    return datetime.strptime(text, fmt).strftime("%d.%m.%Y")
                except Exception:
                    pass

            digits = "".join(ch for ch in text if ch.isdigit())

            if len(digits) == 8:
                candidates = [
                    f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}",
                    f"{digits[4:8]}-{digits[2:4]}-{digits[:2]}",
                ]

                for api_date in candidates:
                    try:
                        return datetime.strptime(api_date, "%Y-%m-%d").strftime("%d.%m.%Y")
                    except Exception:
                        pass

            return text

        except Exception:
            return ""

    def _get_and_register_font(self):
        if not HAS_PDF:
            return "Helvetica"

        try:
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/times.ttf",
                "/usr/share/fonts/truetype/msttcorefonts/arial.ttf",
                "/System/Library/Fonts/Arial.ttf",
            ]

            font_path = None
            for path in font_paths:
                if os.path.exists(path):
                    font_path = path
                    break

            if font_path and font_path.endswith(".ttf"):
                try:
                    font_name = "RussianFont"
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    return font_name
                except Exception:
                    return "Helvetica"

            return "Helvetica"
        except Exception:
            return "Helvetica"

    def create_pdf_attendance(self, data, filename, start_date, end_date, group_filter):
        try:
            if not HAS_PDF:
                self.show_message("Установите библиотеку: pip install reportlab", ft.Colors.ORANGE)
                return

            font_name = self._get_and_register_font()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name

                doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                story = []
                styles = getSampleStyleSheet()

                title_style = ParagraphStyle(
                    "CustomTitle",
                    parent=styles["Heading1"],
                    fontName=font_name,
                    fontSize=16,
                    alignment=1,
                    spaceAfter=30
                )
                normal_style = ParagraphStyle(
                    "CustomNormal",
                    parent=styles["Normal"],
                    fontName=font_name,
                    fontSize=10
                )

                story.append(Paragraph("ОТЧЕТ ПО ПОСЕЩАЕМОСТИ", title_style))
                info_text = f"""
                <b>Период:</b> {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}<br/>
                <b>Группа:</b> {group_filter}<br/>
                <b>Дата формирования:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}<br/>
                <b>Всего записей:</b> {len(data)}
                """
                story.append(Paragraph(info_text, normal_style))
                story.append(Spacer(1, 20))

                if data:
                    table_data = [["Ребенок", "Группа", "Услуга", "Дата", "Статус", "Стоимость"]]
                    total_cost = 0

                    for row in data:
                        child = str(row[0] if row[0] is not None else "")
                        group = str(row[1] if row[1] is not None else "")
                        service = str(row[2] if row[2] is not None else "")
                        date_val = self.format_date_for_view(row[3])
                        status = str(row[4] if row[4] is not None else "")
                        cost = float(row[5] if row[5] is not None else 0)

                        if status == "присутствовал":
                            total_cost += cost

                        table_data.append([child, group, service, date_val, status, f"{cost:.2f}"])

                    table = Table(table_data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 20))
                    story.append(Paragraph(f"<b>Общая стоимость:</b> {total_cost:.2f} руб.", normal_style))
                else:
                    story.append(Paragraph("<b>Нет данных за выбранный период</b>", normal_style))

                doc.build(story)

            self.open_pdf_file(pdf_path)
            self.show_message(f"PDF отчет создан: {filename}", ft.Colors.GREEN)

        except Exception as e:
            self.show_message(f"Ошибка создания PDF: {str(e)}", ft.Colors.RED)

    def create_pdf_payment(self, data, filename, start_date, end_date, group_filter):
        try:
            if not HAS_PDF:
                self.show_message("Установите библиотеку: pip install reportlab", ft.Colors.ORANGE)
                return

            font_name = self._get_and_register_font()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name

                doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                story = []
                styles = getSampleStyleSheet()

                title_style = ParagraphStyle(
                    "CustomTitle",
                    parent=styles["Heading1"],
                    fontName=font_name,
                    fontSize=16,
                    alignment=1,
                    spaceAfter=30
                )
                normal_style = ParagraphStyle(
                    "CustomNormal",
                    parent=styles["Normal"],
                    fontName=font_name,
                    fontSize=10
                )

                story.append(Paragraph("ОТЧЕТ ПО ОПЛАТЕ", title_style))
                story.append(Paragraph(
                    f"<b>Период:</b> {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}<br/><b>Группа:</b> {group_filter}",
                    normal_style
                ))
                story.append(Spacer(1, 20))

                if data:
                    table_data = [["Родитель", "Ребенок", "Группа", "Услуга", "Посещений", "Стоимость"]]
                    total_all = 0

                    for row in data:
                        parent = str(row[0] if row[0] is not None else "")
                        child = str(row[1] if row[1] is not None else "")
                        group = str(row[2] if row[2] is not None else "")
                        service = str(row[3] if row[3] is not None else "")
                        visits = int(row[4] if row[4] is not None else 0)
                        cost = float(row[5] if row[5] is not None else 0)

                        total_all += cost
                        table_data.append([parent, child, group, service, str(visits), f"{cost:.2f}"])

                    table = Table(table_data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 20))
                    story.append(Paragraph(f"<b>Общая сумма:</b> {total_all:.2f} руб.", normal_style))
                else:
                    story.append(Paragraph("<b>Нет данных по оплате</b>", normal_style))

                doc.build(story)

            self.open_pdf_file(pdf_path)
            self.show_message(f"PDF отчет создан: {filename}", ft.Colors.GREEN)

        except Exception as e:
            self.show_message(f"Ошибка создания PDF: {str(e)}", ft.Colors.RED)

    def create_pdf_users(self, data, filename):
        try:
            if not HAS_PDF:
                self.show_message("Установите библиотеку: pip install reportlab", ft.Colors.ORANGE)
                return

            font_name = self._get_and_register_font()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name

                doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4))
                story = []
                styles = getSampleStyleSheet()

                title_style = ParagraphStyle(
                    "CustomTitle",
                    parent=styles["Heading1"],
                    fontName=font_name,
                    fontSize=18,
                    alignment=1,
                    spaceAfter=20
                )

                story.append(Paragraph("ОТЧЕТ ПО ПОЛЬЗОВАТЕЛЯМ", title_style))

                if data:
                    table_data = [["Логин", "Тип", "ФИО", "Ребенок", "Группа"]]
                    for row in data:
                        table_data.append([
                            str(row[0] if row[0] is not None else ""),
                            str(row[1] if row[1] is not None else ""),
                            str(row[2] if row[2] is not None else ""),
                            self.format_date_for_view(row[3]),
                            str(row[4] if row[4] is not None else "")
                        ])

                    table = Table(table_data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(table)

                doc.build(story)

            self.open_pdf_file(pdf_path)
            self.show_message(f"PDF отчет создан: {filename}", ft.Colors.GREEN)

        except Exception as e:
            self.show_message(f"Ошибка создания PDF: {str(e)}", ft.Colors.RED)

    def create_pdf_services(self, data, filename):
        try:
            if not HAS_PDF:
                self.show_message("Установите библиотеку: pip install reportlab", ft.Colors.ORANGE)
                return

            font_name = self._get_and_register_font()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name

                doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                story = []
                styles = getSampleStyleSheet()

                title_style = ParagraphStyle(
                    "CustomTitle",
                    parent=styles["Heading1"],
                    fontName=font_name,
                    fontSize=18,
                    alignment=1,
                    spaceAfter=20
                )

                story.append(Paragraph("ОТЧЕТ ПО УСЛУГАМ", title_style))

                if data:
                    table_data = [["Название", "Описание", "Стоимость", "Воспитатель"]]
                    for row in data:
                        table_data.append([
                            str(row[0] if row[0] is not None else ""),
                            str(row[1] if row[1] is not None else ""),
                            str(row[2] if row[2] is not None else ""),
                            str(row[3] if row[3] is not None else "")
                        ])

                    table = Table(table_data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(table)

                doc.build(story)

            self.open_pdf_file(pdf_path)
            self.show_message(f"PDF отчет создан: {filename}", ft.Colors.GREEN)

        except Exception as e:
            self.show_message(f"Ошибка создания PDF: {str(e)}", ft.Colors.RED)

    def open_pdf_file(self, filepath):
        try:
            import platform
            import subprocess

            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":
                subprocess.call(["open", filepath])
            elif platform.system() == "Linux":
                subprocess.call(["xdg-open", filepath])
            else:
                self.show_message(f"PDF сохранен: {filepath}", ft.Colors.GREEN)

        except Exception as e:
            print(f"Не удалось открыть PDF автоматически: {e}")
            self.show_message(f"PDF создан: {filepath}", ft.Colors.GREEN)

    def get_attendance_data(self, start_date, end_date, group_filter):
        return self.db.get_attendance_report_data(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            group_filter
        )

    def get_payment_data(self, start_date, end_date, group_filter):
        return self.db.get_payment_report_data(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            group_filter
        )

    def get_users_data(self):
        return self.db.get_users_report_data()

    def get_services_data(self):
        return self.db.get_services_report_data()

    def save_csv_attendance(self, data, filename):
        if not data:
            self.show_message("Нет данных для экспорта", ft.Colors.YELLOW)
            return

        headers = ["Ребенок", "Группа", "Услуга", "Дата", "Статус", "Стоимость"]

        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8-sig") as tmp:
                writer = csv.writer(tmp, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)
                for row in data:
                    writer.writerow([
                        str(row[0] if row[0] is not None else ""),
                        str(row[1] if row[1] is not None else ""),
                        str(row[2] if row[2] is not None else ""),
                        str(row[3] if row[3] is not None else ""),
                        str(row[4] if row[4] is not None else ""),
                        str(row[5] if row[5] is not None else "0")
                    ])
                tmp_path = tmp.name

            self.show_message(f"Отчет сохранен: {filename}", ft.Colors.GREEN)
            self.open_csv_in_excel(tmp_path)

        except Exception as e:
            self.show_message(f"Ошибка сохранения CSV: {str(e)}", ft.Colors.RED)

    def save_csv_payment(self, data, filename):
        if not data:
            self.show_message("Нет данных для экспорта", ft.Colors.YELLOW)
            return

        headers = ["Родитель", "Ребенок", "Группа", "Услуга", "Посещений", "Стоимость"]

        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8-sig") as tmp:
                writer = csv.writer(tmp, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)

                for row in data:
                    writer.writerow([
                        str(row[0] if row[0] is not None else ""),
                        str(row[1] if row[1] is not None else ""),
                        str(row[2] if row[2] is not None else ""),
                        str(row[3] if row[3] is not None else ""),
                        str(row[4] if row[4] is not None else "0"),
                        str(row[5] if row[5] is not None else "0"),
                    ])
                tmp_path = tmp.name

            self.show_message(f"Отчет сохранен: {filename}", ft.Colors.GREEN)
            self.open_csv_in_excel(tmp_path)

        except Exception as e:
            self.show_message(f"Ошибка сохранения CSV: {str(e)}", ft.Colors.RED)

    def save_csv_users(self, data, filename):
        if not data:
            self.show_message("Нет данных для экспорта", ft.Colors.YELLOW)
            return

        headers = ["Логин", "Тип", "ФИО", "Ребенок", "Группа"]

        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8-sig") as tmp:
                writer = csv.writer(tmp, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)

                for row in data:
                    writer.writerow([
                        str(row[0] if row[0] is not None else ""),
                        str(row[1] if row[1] is not None else ""),
                        str(row[2] if row[2] is not None else ""),
                        str(row[3] if row[3] is not None else ""),
                        str(row[4] if row[4] is not None else "")
                    ])
                tmp_path = tmp.name

            self.show_message(f"Отчет сохранен: {filename}", ft.Colors.GREEN)
            self.open_csv_in_excel(tmp_path)

        except Exception as e:
            self.show_message(f"Ошибка сохранения CSV: {str(e)}", ft.Colors.RED)

    def save_csv_services(self, data, filename):
        if not data:
            self.show_message("Нет данных для экспорта", ft.Colors.YELLOW)
            return

        headers = ["Название", "Описание", "Стоимость", "Воспитатель"]

        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8-sig") as tmp:
                writer = csv.writer(tmp, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)

                for row in data:
                    writer.writerow([
                        str(row[0] if row[0] is not None else ""),
                        str(row[1] if row[1] is not None else ""),
                        str(row[2] if row[2] is not None else "0"),
                        str(row[3] if row[3] is not None else "")
                    ])
                tmp_path = tmp.name

            self.show_message(f"Отчет сохранен: {filename}", ft.Colors.GREEN)
            self.open_csv_in_excel(tmp_path)

        except Exception as e:
            self.show_message(f"Ошибка сохранения CSV: {str(e)}", ft.Colors.RED)

    def open_csv_in_excel(self, filepath):
        try:
            import platform
            import subprocess

            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":
                try:
                    subprocess.call(["open", "-a", "Microsoft Excel", filepath])
                except Exception:
                    subprocess.call(["open", filepath])
            elif platform.system() == "Linux":
                try:
                    subprocess.call(["libreoffice", "--calc", filepath])
                except Exception:
                    subprocess.call(["xdg-open", filepath])
            else:
                print(f"Файл сохранен: {filepath}")

        except Exception as e:
            print(f"Не удалось открыть файл автоматически: {e}")
            print(f"Файл сохранен в: {filepath}")

    # =========================
    # ОБЩИЕ МЕТОДЫ
    # =========================
    def open_dialog(self, dialog: ft.AlertDialog):
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

    def close_dialog(self, dialog: ft.AlertDialog):
        try:
            dialog.open = False
            self.page.update()
        except Exception as e:
            print(f"Ошибка при закрытии диалога: {e}")

    def delete_service(self, service_id):
        try:
            confirm_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Подтверждение удаления"),
                content=ft.Text(f"Вы уверены, что хотите удалить услугу (ID: {service_id})?"),
                actions=[
                    ft.TextButton("Да", on_click=lambda e: self.confirm_service_delete(service_id, confirm_dialog)),
                    ft.TextButton("Нет", on_click=lambda e: self.close_dialog(confirm_dialog))
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.open_dialog(confirm_dialog)
        except Exception as e:
            print(f"Ошибка в delete_service: {e}")
            self.show_message(f"Ошибка: {e}", ft.Colors.RED)

    def confirm_service_delete(self, service_id, dialog):
        try:
            self.close_dialog(dialog)
            success = self.db.delete_service(service_id)
            if success:
                self.show_message("Услуга удалена", ft.Colors.GREEN)
                self.show_services_management()
            else:
                self.show_message("Ошибка при удалении услуги", ft.Colors.RED)
        except Exception as e:
            print(f"Ошибка в confirm_service_delete: {e}")
            self.show_message(f"Ошибка: {e}", ft.Colors.RED)

    def delete_user(self, user_id):
        try:
            if not user_id:
                self.show_message("Не удалось определить пользователя для удаления", ft.Colors.RED)
                return

            confirm_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Подтверждение удаления"),
                content=ft.Text("Вы уверены, что хотите удалить пользователя?"),
                actions=[
                    ft.TextButton("Да", on_click=lambda e: self.confirm_user_delete(user_id, confirm_dialog)),
                    ft.TextButton("Нет", on_click=lambda e: self.close_dialog(confirm_dialog))
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.open_dialog(confirm_dialog)
        except Exception as e:
            print(f"Ошибка в delete_user: {e}")
            self.show_message(f"Ошибка: {e}", ft.Colors.RED)

    def confirm_user_delete(self, user_id, dialog):
        try:
            self.close_dialog(dialog)
            success = self.db.delete_user(user_id)
            if success:
                self.show_message("Пользователь удален", ft.Colors.GREEN)
                self.show_users_management()
            else:
                self.show_message("Ошибка при удалении пользователя", ft.Colors.RED)
        except Exception as e:
            print(f"Ошибка в confirm_user_delete: {e}")
            self.show_message(f"Ошибка: {e}", ft.Colors.RED)

    def show_message(self, message, color):
        try:
            snackbar = ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                bgcolor=color,
                duration=4000,
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