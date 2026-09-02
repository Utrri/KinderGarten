import flet as ft
from database import KindergartenDB
from auth import AuthSystem


def close_app(page: ft.Page):
    """Закрытие приложения."""
    try:
        page.window_destroy()
    except Exception:
        page.clean()
        page.add(ft.Text("Приложение можно закрыть.", size=18))
        page.update()


def logout_user(page: ft.Page, db):
    """Выход из аккаунта и возврат на экран входа."""
    try:
        page.client_storage.remove("current_user")
    except Exception:
        pass

    auth = AuthSystem(page, db)
    auth.show_login()


def show_user_interface(page, user, db):
    """Открытие интерфейса в зависимости от роли пользователя."""
    try:
        user_type = user[3]
        username = user[1]

        if user_type == "admin" or username == "admin":
            from admin_interface import AdminInterface

            admin_interface = AdminInterface(page, user, db)
            admin_interface.show_interface()

        elif user_type == "parent":
            from parent_interface import ParentInterface

            parent_interface = ParentInterface(page, user, db)
            parent_interface.show_interface()

        elif user_type == "teacher":
            from teacher_interface import TeacherInterface

            teacher_interface = TeacherInterface(page, user, db)
            teacher_interface.show_interface()

        else:
            page.clean()
            page.add(
                ft.Text(
                    f"Неизвестный тип пользователя: {user_type}",
                    color=ft.Colors.RED,
                )
            )
            page.update()

    except Exception as e:
        page.clean()
        page.add(
            ft.Column(
                [
                    ft.Text(
                        "Ошибка открытия интерфейса",
                        size=20,
                        color=ft.Colors.RED,
                    ),
                    ft.Text(f"Ошибка: {str(e)}", size=14),
                    ft.ElevatedButton(
                        "Назад ко входу",
                        on_click=lambda e: AuthSystem(page, db).show_login(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()


def main(page: ft.Page):
    try:

        page.title = "Детский сад"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.padding = 20


        db = KindergartenDB()

        auth = AuthSystem(page, db)

        saved_user = None

        try:
            saved_user = page.client_storage.get("current_user")
        except Exception as e:
            saved_user = None

        if saved_user:
            show_user_interface(page, saved_user, db)
        else:
            auth.show_login()

    except Exception as e:
        print(f"ОШИБКА ЗАПУСКА: {e}")

        page.clean()
        page.add(
            ft.Column(
                [
                    ft.Text(
                        "Ошибка запуска приложения",
                        size=20,
                        color=ft.Colors.RED,
                    ),
                    ft.Text(f"Ошибка: {str(e)}", size=14),
                    ft.ElevatedButton(
                        "Попробовать снова",
                        on_click=lambda e: main(page),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()


if __name__ == "__main__":
    ft.run(main)