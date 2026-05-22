from abc import ABC, abstractmethod


class UIBase(ABC):
    """Abstract UI interface."""

    @abstractmethod
    def display_narrative(self, text: str) -> None:
        """Display narrative/story text."""
        ...

    @abstractmethod
    def display_state(self, state) -> None:
        """Display the full player state panel (stats + time + location)."""
        ...

    @abstractmethod
    def get_choice(self, choices: list) -> int:
        """[Choice Mode] Display choices and return selected index (0-based)."""
        ...

    @abstractmethod
    def get_free_text(self, prompt: str = "") -> str:
        """[Free-text Mode] Get free-text input from the player."""
        ...

    @abstractmethod
    def show_message(self, text: str) -> None:
        """Display a system message or notification."""
        ...

    @abstractmethod
    def get_input(self, prompt: str) -> str:
        """Get generic text input."""
        ...

    @abstractmethod
    def check_command(self, text: str) -> str | None:
        """Check if input is a system command. Returns command name or None."""
        ...

    # === v4 new methods ===

    @abstractmethod
    def display_location(self, location_name: str, npcs_present: list, loc_info: dict) -> None:
        """Display current location info and present NPCs."""
        ...

    @abstractmethod
    def display_relationship_table(self, npcs: list) -> None:
        """Display affection table for all NPCs."""
        ...

    @abstractmethod
    def display_outfit(self, outfit, gender: str = "男") -> None:
        """Display current outfit."""
        ...

    @abstractmethod
    def display_datetime(self, gdt, holidays: list = None) -> None:
        """Display current game date/time."""
        ...
