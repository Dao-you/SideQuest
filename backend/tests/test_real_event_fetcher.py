"""Tests for selecting trustworthy Taipei locations from iCulture schedules."""

from app.services.real_event_fetcher import RealEventFetcher


def test_selects_taipei_schedule_instead_of_first_out_of_city_entry():
    fetcher = RealEventFetcher()
    show = {
        "showInfo": [
            {
                "locationName": "衛武營國家藝術文化中心",
                "location": "高雄市鳳山區三多一路1號",
                "latitude": "22.6230",
                "longitude": "120.3424",
            },
            {
                "locationName": "國家音樂廳（臺北市）",
                "location": "臺北市中正區中山南路21-1號",
                "latitude": "25.0368",
                "longitude": "121.5190",
            },
        ]
    }

    selected = fetcher._select_taipei_show_info(show)

    assert selected is not None
    show_info, lat, lng = selected
    assert show_info["locationName"] == "國家音樂廳（臺北市）"
    assert (lat, lng) == (25.0368, 121.5190)


def test_rejects_taipei_entry_without_valid_coordinates():
    fetcher = RealEventFetcher()
    show = {
        "showInfo": [
            {
                "locationName": "臺北市藝文場館",
                "location": "臺北市中正區",
                "latitude": "0",
                "longitude": "0",
            }
        ]
    }

    assert fetcher._select_taipei_show_info(show) is None

