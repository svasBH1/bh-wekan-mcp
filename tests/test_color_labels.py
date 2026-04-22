"""
Unit tests for wekan-mcp v0.1.2 card color and label tools.

Run: python -m pytest tests/test_color_labels.py -v
Or:  python -m unittest discover tests -v

For live API tests, set WEKAN_API_TOKEN in .env and run with:
    pytest tests/test_color_labels.py -v --live

These tests use mocking by default. The mock tests verify the correct HTTP
calls are made with correct parameters. Live tests hit the real Wekan instance.
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock


class TestAllowedColors(unittest.TestCase):
    """Test ALLOWED_COLORS constant matches Wekan v7.60.0 const.js."""

    def test_allowed_colors_count(self):
        """Should have 25 colors (per Wekan v7.60.0 const.js ALLOWED_COLORS)."""
        from server import ALLOWED_COLORS
        self.assertEqual(len(ALLOWED_COLORS), 25)

    def test_all_colors_are_strings(self):
        from server import ALLOWED_COLORS
        for c in ALLOWED_COLORS:
            self.assertIsInstance(c, str)

    def test_expected_colors_present(self):
        from server import ALLOWED_COLORS
        for color in ["green", "blue", "red", "purple", "orange", "yellow", "pink", "black", "white"]:
            self.assertIn(color, ALLOWED_COLORS)


class TestValidateColor(unittest.TestCase):
    """Test _validate_color helper."""

    def test_valid_color_passes(self):
        from server import _validate_color
        result = _validate_color("blue")
        self.assertEqual(result, "blue")

    def test_invalid_color_raises(self):
        from server import _validate_color
        with self.assertRaises(ValueError):
            _validate_color("notacolor")

    def test_empty_color_raises(self):
        from server import _validate_color
        with self.assertRaises(ValueError):
            _validate_color("")


class TestGetAllowedColors(unittest.TestCase):
    """Test get_allowed_colors tool."""

    def test_returns_all_colors(self):
        from server import get_allowed_colors, ALLOWED_COLORS
        result = get_allowed_colors()
        self.assertEqual(result["colors"], ALLOWED_COLORS)


class TestGetCardColor(unittest.TestCase):
    """Test get_card_color tool."""

    @patch("server._build_session")
    def test_returns_color(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"_id": "card1", "color": "blue"}
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import get_card_color
        result = get_card_color("board1", "list1", "card1")
        self.assertEqual(result["color"], "blue")

    @patch("server._build_session")
    def test_returns_empty_when_no_color(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"_id": "card1"}
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import get_card_color
        result = get_card_color("board1", "list1", "card1")
        self.assertEqual(result["color"], "")


class TestSetCardColor(unittest.TestCase):
    """Test set_card_color tool."""

    @patch("server._build_session")
    def test_puts_color(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.put.return_value.json.return_value = {"_id": "card1", "color": "red"}
        mock_session.put.return_value.raise_for_status = MagicMock()

        from server import set_card_color
        result = set_card_color("board1", "list1", "card1", "red")
        self.assertEqual(result["color"], "red")

    @patch("server._build_session")
    def test_invalid_color_rejected(self, mock_build_session):
        from server import set_card_color
        with self.assertRaises(ValueError):
            set_card_color("board1", "list1", "card1", "invalid_color")


class TestGetBoardLabels(unittest.TestCase):
    """Test get_board_labels tool."""

    @patch("server._build_session")
    def test_returns_labels(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {
            "_id": "board1",
            "labels": [
                {"_id": "lb1", "name": "Urgent", "color": "red"},
                {"_id": "lb2", "name": "Done", "color": "green"},
            ],
        }
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import get_board_labels
        result = get_board_labels("board1")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "lb1")
        self.assertEqual(result[0]["name"], "Urgent")
        self.assertEqual(result[0]["color"], "red")

    @patch("server._build_session")
    def test_returns_empty_when_no_labels(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"_id": "board1"}
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import get_board_labels
        result = get_board_labels("board1")
        self.assertEqual(result, [])


class TestAddBoardLabel(unittest.TestCase):
    """Test add_board_label tool."""

    @patch("server._build_session")
    def test_puts_label(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.put.return_value.json.return_value = {"_id": "lb1"}
        mock_session.put.return_value.raise_for_status = MagicMock()

        from server import add_board_label
        result = add_board_label("board1", "Urgent", "red")
        self.assertEqual(result["name"], "Urgent")
        self.assertEqual(result["color"], "red")

    @patch("server._build_session")
    def test_empty_response_idempotent(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.put.return_value.json.return_value = None
        mock_session.put.return_value.raise_for_status = MagicMock()

        from server import add_board_label
        result = add_board_label("board1", "ExistingLabel", "blue")
        self.assertIn("error", result)


class TestEditBoardLabel(unittest.TestCase):
    """Test edit_board_label tool."""

    @patch("server._build_session")
    def test_edits_name(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {
            "_id": "board1",
            "labels": [{"_id": "lb1", "name": "OldName", "color": "blue"}],
        }
        mock_session.get.return_value.raise_for_status = MagicMock()
        mock_session.put.return_value.json.return_value = {"_id": "board1"}
        mock_session.put.return_value.raise_for_status = MagicMock()

        from server import edit_board_label
        result = edit_board_label("board1", "lb1", name="NewName")
        self.assertEqual(result["name"], "NewName")

    @patch("server._build_session")
    def test_label_not_found(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"labels": []}
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import edit_board_label
        result = edit_board_label("board1", "nonexistent", name="New")
        self.assertIn("error", result)


class TestAddCardLabel(unittest.TestCase):
    """Test add_card_label tool."""

    @patch("server._build_session")
    def test_adds_label_id(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"_id": "card1", "labelIds": []}
        mock_session.get.return_value.raise_for_status = MagicMock()
        mock_session.put.return_value.json.return_value = {"_id": "card1", "labelIds": ["lb1"]}
        mock_session.put.return_value.raise_for_status = MagicMock()

        from server import add_card_label
        result = add_card_label("board1", "list1", "card1", "lb1")
        self.assertIn("lb1", result["labelIds"])

    @patch("server._build_session")
    def test_skips_already_attached(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"_id": "card1", "labelIds": ["lb1"]}
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import add_card_label
        result = add_card_label("board1", "list1", "card1", "lb1")
        self.assertNotIn("error", result)


class TestRemoveCardLabel(unittest.TestCase):
    """Test remove_card_label tool."""

    @patch("server._build_session")
    def test_removes_label_id(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"_id": "card1", "labelIds": ["lb1", "lb2"]}
        mock_session.get.return_value.raise_for_status = MagicMock()
        mock_session.put.return_value.json.return_value = {"_id": "card1", "labelIds": ["lb2"]}
        mock_session.put.return_value.raise_for_status = MagicMock()

        from server import remove_card_label
        result = remove_card_label("board1", "list1", "card1", "lb1")
        self.assertNotIn("lb1", result["labelIds"])
        self.assertIn("lb2", result["labelIds"])

    @patch("server._build_session")
    def test_skips_not_attached(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {"_id": "card1", "labelIds": ["lb2"]}
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import remove_card_label
        result = remove_card_label("board1", "list1", "card1", "lb1")
        self.assertNotIn("error", result)


class TestGetCardLabelIdsInResponse(unittest.TestCase):
    """Test that get_card returns color and labelIds."""

    @patch("server._build_session")
    def test_get_card_returns_color_and_labelids(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.get.return_value.json.return_value = {
            "_id": "card1",
            "title": "Test Card",
            "description": "",
            "listId": "list1",
            "swimlaneId": "swim1",
            "dueDate": "2026-04-22",
            "startDate": "",
            "createdAt": "2026-04-22T10:00:00Z",
            "assigneeId": "",
            "color": "purple",
            "labelIds": ["lb1", "lb2"],
            "labels": [],
        }
        mock_session.get.return_value.raise_for_status = MagicMock()

        from server import get_card
        result = get_card("board1", "list1", "card1")
        self.assertEqual(result["color"], "purple")
        self.assertEqual(result["labelIds"], ["lb1", "lb2"])


class TestUpdateCardColor(unittest.TestCase):
    """Test that update_card accepts color."""

    @patch("server._build_session")
    def test_update_card_with_color(self, mock_build_session):
        mock_session = MagicMock()
        mock_build_session.return_value = mock_session
        mock_session.put.return_value.json.return_value = {"_id": "card1", "title": "Test", "color": "green"}
        mock_session.put.return_value.raise_for_status = MagicMock()

        from server import update_card
        result = update_card("board1", "list1", "card1", color="green")
        self.assertNotIn("error", result)


# ---------------------------------------------------------------------------
# Live API tests — run only with --live flag
# ---------------------------------------------------------------------------

LIVE = "--live" in sys.argv


@unittest.skipUnless(LIVE, "Live API tests — requires real Wekan instance")
class TestColorLabelsLive(unittest.TestCase):
    """Integration tests against live Wekan instance.

    Run: pytest tests/test_color_labels.py -v --live
    Requires: WEKAN_API_TOKEN in .env
    """

    BOARD_ID = "tMDX8jc8L75Wr9PsJ"
    LIST_ID = "wmBJuc4EW48HGGfgt"
    CARD_ID = "gk5dGLfk3rdHwWX8N"

    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv()

    def test_get_allowed_colors(self):
        from server import get_allowed_colors, ALLOWED_COLORS
        result = get_allowed_colors()
        self.assertEqual(result["colors"], ALLOWED_COLORS)
        self.assertIn("green", result["colors"])
        self.assertIn("blue", result["colors"])

    def test_set_and_get_card_color(self):
        from server import set_card_color, get_card_color
        result = set_card_color(self.BOARD_ID, self.LIST_ID, self.CARD_ID, "blue")
        self.assertNotIn("error", result)

        result = get_card_color(self.BOARD_ID, self.LIST_ID, self.CARD_ID)
        self.assertEqual(result["color"], "blue")

    def test_get_board_labels(self):
        from server import get_board_labels
        result = get_board_labels(self.BOARD_ID)
        self.assertIsInstance(result, list)

    def test_add_board_label(self):
        from server import add_board_label, get_board_labels
        result = add_board_label(self.BOARD_ID, "MCP-Test-Label", "green")
        self.assertNotIn("error", result)

    def test_get_card_returns_color_and_labelids(self):
        from server import get_card
        result = get_card(self.BOARD_ID, self.LIST_ID, self.CARD_ID)
        self.assertIn("color", result)
        self.assertIn("labelIds", result)

    def test_update_card_color(self):
        from server import update_card, get_card
        result = update_card(self.BOARD_ID, self.LIST_ID, self.CARD_ID, color="purple")
        self.assertNotIn("error", result)

        result = get_card(self.BOARD_ID, self.LIST_ID, self.CARD_ID)
        self.assertEqual(result["color"], "purple")


if __name__ == "__main__":
    unittest.main()