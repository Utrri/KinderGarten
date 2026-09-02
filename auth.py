import flet as ft


class AuthSystem:
    def __init__(self, page, db):
        self.page = page
        self.db = db

    def show_login(self):
        self.page.clean()
        self.page.title = "Вход в систему"
        self.page.bgcolor = "#F4F6F8"

        self.username_field = ft.TextField(
            label="Логин",
            width=320,
            autofocus=True,
            border_radius=10,
        )

        self.password_field = ft.TextField(
            label="Пароль",
            password=True,
            can_reveal_password=True,
            width=320,
            border_radius=10,
        )

        async def close_app(e):
            await self.page.window.close()

        def login_click(e):
            login_button.text = "Вход..."
            login_button.disabled = True
            self.page.update()

            username = (self.username_field.value or "").strip()
            password = self.password_field.value or ""

            if not username or not password:
                self.show_error("Введите логин и пароль")
                login_button.text = "Войти"
                login_button.disabled = False
                self.page.update()
                return

            try:
                user = self.db.login_user(username, password)

                if user:
                    try:
                        self.page.client_storage.set("current_user", list(user))
                    except Exception:
                        pass

                    self.show_success("Вход выполнен успешно!")

                    from main import show_user_interface
                    show_user_interface(self.page, user, self.db)
                else:
                    self.show_error("Неверный логин или пароль")
                    self.password_field.value = ""
                    login_button.text = "Войти"
                    login_button.disabled = False
                    self.page.update()

            except Exception as ex:
                self.show_error(f"Ошибка подключения: {str(ex)}")
                login_button.text = "Войти"
                login_button.disabled = False
                self.page.update()

        login_button = ft.ElevatedButton(
            "Войти",
            on_click=login_click,
            width=320,
            height=48,
        )

        close_button = ft.IconButton(
            icon=ft.Icons.LOGOUT,
            tooltip="Закрыть приложение",
            on_click=close_app,
            icon_color=ft.Colors.RED,
        )

        top_bar = ft.Row(
            controls=[
                ft.Container(expand=True),
                close_button,
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        login_form = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Вход в систему",
                        size=24,
                        weight="bold",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    self.username_field,
                    self.password_field,
                    login_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

        self.page.add(
            ft.Column(
                controls=[
                    top_bar,
                    login_form,
                ],
                expand=True,
            )
        )

        self.page.update()

    def show_error(self, message):
        try:
            snackbar = ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                bgcolor=ft.Colors.RED,
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
            print(f"Ошибка при показе ошибки: {e}")

    def show_success(self, message):
        try:
            snackbar = ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                bgcolor=ft.Colors.GREEN,
                duration=2000,
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