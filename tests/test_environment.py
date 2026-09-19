"""Verifica o smoke check composto, sem rede e sem credenciais."""

from scripts.verify_environment import main


def test_environment_smoke() -> None:
    main()
