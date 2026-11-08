from valutatrade_hub.cli.interface import handle_command, run


def main() -> None:
    """Запускает CLI-приложение."""
    print("Добро пожаловать в ValutaTrade Hub!")
    print("Введите команду или 'exit' для выхода.")

    while True:
        try:
            command = input("valutatrade> ").strip()

            if command.lower() == "exit":
                print("До свидания!")
                break

            result = handle_command(command)
            print(result)

        except (ValueError, KeyError, TypeError) as error:
            print(f"Ошибка: {error}")

        except KeyboardInterrupt:
            print("\nДо свидания!")
            break


if __name__ == "__main__":
    run()
