"""Initialize the farm database with sample plots."""

from src.database import FarmDatabase


def setup_plots() -> None:
    """Initialize database with 3 Telugu farmer plots."""
    db = FarmDatabase()
    db.init_database()

    plots = [
        {
            "name_en": "Thurpu Polam",
            "name_te": "తూర్పు పొలం",
            "crop_en": "Jowar",
            "crop_te": "జొన్న",
            "size": 1.75,
            "lat": 16.3700,   # TODO: replace with actual GPS
            "lon": 80.7200,   # Emani Duggirala Mandal, AP
            "freq": 7,
        },
        {
            "name_en": "Athota Road Polam",
            "name_te": "ఆత్తోట రోడ్ పొలం",
            "crop_en": "Jowar",
            "crop_te": "జొన్న",
            "size": 1.0,
            "lat": 16.322104,
            "lon": 80.667237,
            "freq": 7,
            "corners": [
                {"lat": 16.322454, "lon": 80.666894},
                {"lat": 16.322228, "lon": 80.666828},
                {"lat": 16.322179, "lon": 80.667033},
                {"lat": 16.321829, "lon": 80.667020},
                {"lat": 16.321687, "lon": 80.667791},
                {"lat": 16.322247, "lon": 80.667856},
            ],
        },
        {
            "name_en": "Munnagi Road Polam",
            "name_te": "ముణగి రోడ్ పొలం",
            "crop_en": "Jowar",
            "crop_te": "జొన్న",
            "size": 0.8,
            "lat": 16.3680,   # TODO: replace with actual GPS
            "lon": 80.7180,   # Emani Duggirala Mandal, AP
            "freq": 7,
        },
    ]

    for plot in plots:
        try:
            plot_id = db.add_plot(
                plot["name_en"],
                plot["name_te"],
                plot["crop_en"],
                plot["crop_te"],
                plot["size"],
                plot["lat"],
                plot["lon"],
                plot["freq"],
                corners=plot.get("corners"),
            )
            print(f"✓ అందించిన పొలం | Plot Added: {plot['name_en']} ({plot['name_te']}) - ID: {plot_id}")
        except Exception as e:
            print(f"✗ Error adding plot {plot['name_en']}: {e}")

    print("\n✓ డేటాబేస్ సెటప్ పూర్తైంది | Database setup complete!")
    print("✓ అన్ని 3 పొలాలు సంরక్షించబడ్డాయి | All 3 plots registered")


if __name__ == "__main__":
    setup_plots()
