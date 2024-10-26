from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, date, timedelta
import io
import base64
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import random

app = Flask(__name__)

logging.basicConfig(filename="app.log", level=logging.INFO)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://",
)

COLOR_SCHEMES = {
    "starry_night": {
        "name": "Starry Night",
        "background": "#0C1445",
        "past": "#FFD700",
        "future": "#4A6DB5",
    },
    "sunflowers": {
        "name": "Sunflowers",
        "background": "#2C3E50",
        "past": "#F1C40F",
        "future": "#E67E22",
    },
    "water_lilies": {
        "name": "Water Lilies",
        "background": "#1A5276",
        "past": "#82E0AA",
        "future": "#85C1E9",
    },
    "the_scream": {
        "name": "The Scream",
        "background": "#34495E",
        "past": "#E74C3C",
        "future": "#F39C12",
    },
    "girl_with_pearl_earring": {
        "name": "Girl with a Pearl Earring",
        "background": "#2C3E50",
        "past": "#D35400",
        "future": "#F1C40F",
    },
    "cafe_terrace_at_night": {
        "name": "Café Terrace at Night",
        "background": "#1B2631",
        "past": "#F4D03F",
        "future": "#5DADE2",
    },
    "persistence_of_memory": {
        "name": "The Persistence of Memory",
        "background": "#273746",
        "past": "#D68910",
        "future": "#5DADE2",
    },
    "birth_of_venus": {
        "name": "The Birth of Venus",
        "background": "#21618C",
        "past": "#F1948A",
        "future": "#D4E6F1",
    },
    "the_kiss": {
        "name": "The Kiss",
        "background": "#1C2833",
        "past": "#F4D03F",
        "future": "#85C1E9",
    },
    "mona_lisa": {
        "name": "Mona Lisa",
        "background": "#212F3D",
        "past": "#B7950B",
        "future": "#7FB3D5",
    },
}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        birth_date = datetime.strptime(request.form["birth_date"], "%Y-%m-%d")
        name = request.form["name"]
        life_expectancy = int(request.form["life_expectancy"])

        weeks_lived = calculate_weeks_lived(birth_date)

        today = datetime.now()
        days_lived = (today - birth_date).days
        years_lived = days_lived // 365
        months_lived = days_lived // 30
        seconds_lived = days_lived * 24 * 60 * 60

        total_days = int(life_expectancy * 365.25)  # Consider leap years
        total_weeks = total_days // 7
        weeks_remaining = total_weeks - weeks_lived

        current_date = today.strftime("%Y%m%d")
        # Generate filename
        base_filename = (
            f"life_weeks_{name}_{current_date}"
            if name
            else f"life_weeks_{current_date}"
        )

        images = {}
        color_scheme_names = {}
        filenames = {}
        for scheme, data in COLOR_SCHEMES.items():
            img = create_life_weeks_image(weeks_lived, name, scheme, total_weeks)
            img_io = io.BytesIO()
            img.save(img_io, "PNG")
            img_io.seek(0)
            img_base64 = base64.b64encode(img_io.getvalue()).decode("ascii")
            images[scheme] = img_base64
            color_scheme_names[scheme] = data["name"]
            filenames[scheme] = f"{base_filename}_{data['name']}.png"

        calculation_text = f"""
        <p>{'Dear ' + name if name else 'You'} were born on <strong>{birth_date.strftime('%B %d, %Y')}</strong>.</p>
        <p>As of <strong>{today.strftime('%B %d, %Y')}</strong>:</p>
        <ul>
            <li>You have lived for <strong>{years_lived}</strong> years</li>
            <li>This is equivalent to <strong>{months_lived}</strong> months</li>
            <li>Or <strong>{weeks_lived}</strong> weeks</li>
            <li>Precisely <strong>{days_lived}</strong> days</li>
            <li>Which is an astonishing <strong>{seconds_lived:,}</strong> seconds</li>
        </ul>
        <p>Based on your chosen life expectancy of <strong>{life_expectancy}</strong> years:</p>
        <ul>
            <li>You have about <strong>{weeks_remaining}</strong> weeks left</li>
            <li>This represents <strong>{(weeks_remaining/total_weeks*100):.2f}%</strong> of your total life weeks</li>
        </ul>
        <p>Make the most of the present and create a fantastic life!</p>
        """

        return jsonify(
            {
                "images": images,
                "calculation_text": calculation_text,
                "color_scheme_names": color_scheme_names,
                "filenames": filenames,
            }
        )

    # Set default date to 25 years ago
    default_date = (date.today() - timedelta(days=365 * 25)).strftime("%Y-%m-%d")
    return render_template("index.html", default_date=default_date)


@app.route("/download", methods=["POST"])
@limiter.limit("5 per minute")
def download():
    logging.info(f"Download request from {request.remote_addr}")
    img_data = base64.b64decode(request.json["image"])
    filename = request.json["filename"]
    img_io = io.BytesIO(img_data)
    img_io.seek(0)

    img_base64 = base64.b64encode(img_io.getvalue()).decode("ascii")
    data_url = f"data:image/png;base64,{img_base64}"

    return jsonify({"data_url": data_url, "filename": filename})


def create_gradient_background(width, height, color1, color2):
    base = Image.new("RGB", (width, height), color1)
    top = Image.new("RGB", (width, height), color2)
    mask = Image.new("L", (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


def add_stars(img, star_count=200):
    draw = ImageDraw.Draw(img)
    width, height = img.size
    for _ in range(star_count):
        x = random.randint(0, width)
        y = random.randint(0, height)
        size = random.randint(1, 3)
        draw.ellipse([x, y, x + size, y + size], fill="white")
    return img


def create_life_weeks_image(weeks_lived, name, color_scheme, total_weeks):
    max_width, max_height = 1200, 2160
    colors = COLOR_SCHEMES[color_scheme]

    background = create_gradient_background(
        max_width, max_height, colors["background"], colors["future"]
    )

    background = add_stars(background)

    overlay = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    weeks_per_row = min(52, max(26, (total_weeks + 99) // 100))
    rows = (total_weeks + weeks_per_row - 1) // weeks_per_row

    try:
        title_font_size = min(60, max(30, int(max_width / 20)))
        legend_font_size = min(30, max(20, int(max_width / 40)))
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", title_font_size
        )
        legend_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", legend_font_size
        )
    except IOError:
        title_font = ImageFont.load_default()
        legend_font = ImageFont.load_default()

    text_color = get_contrasting_color(colors["background"])

    title = f"{name}'s Week {weeks_lived}" if name else f"Week {weeks_lived}"
    title_width = draw.textlength(title, font=title_font)
    draw.text(
        ((max_width - title_width) / 2, 60), title, font=title_font, fill=text_color
    )

    grid_width = max_width - 240
    grid_height = max_height - 300
    start_x, start_y = (max_width - grid_width) / 2, 150
    cell_width, cell_height = grid_width / weeks_per_row, grid_height / rows

    for week in range(total_weeks):
        row = week // weeks_per_row
        col = week % weeks_per_row
        x = start_x + col * cell_width
        y = start_y + row * cell_height

        if week < weeks_lived:
            color = colors["past"]
            alpha = int(255 * (1 - (weeks_lived - week) / weeks_lived))
        else:
            color = colors["future"]
            alpha = int(255 * ((week - weeks_lived) / (total_weeks - weeks_lived)))

        r, g, b = tuple(int(color[1:][i : i + 2], 16) for i in (0, 2, 4))
        color_with_alpha = (r, g, b, alpha)

        if week == weeks_lived - 1:
            draw.rectangle(
                [x - 2, y - 2, x + cell_width + 1, y + cell_height + 1], fill=text_color
            )

        draw.rectangle(
            [x, y, x + cell_width - 1, y + cell_height - 1],
            fill=color_with_alpha,
            outline=colors["background"],
        )

    legend_y = start_y + grid_height + 40
    legend_width = 400
    legend_start_x = (max_width - legend_width) / 2

    draw.rectangle(
        [legend_start_x, legend_y, legend_start_x + 30, legend_y + 30],
        fill=colors["past"],
        outline="#ecf0f1",
    )
    draw.text(
        (legend_start_x + 40, legend_y), "Weeks lived", font=legend_font, fill="#ecf0f1"
    )

    draw.rectangle(
        [
            legend_start_x + legend_width / 2,
            legend_y,
            legend_start_x + legend_width / 2 + 30,
            legend_y + 30,
        ],
        fill=colors["future"],
        outline="#ecf0f1",
    )
    draw.text(
        (legend_start_x + legend_width / 2 + 40, legend_y),
        "Future weeks",
        font=legend_font,
        fill="#ecf0f1",
    )

    img = Image.alpha_composite(background.convert("RGBA"), overlay)
    return img.convert("RGB")


def get_contrasting_color(background_color):
    r = int(background_color[1:3], 16)
    g = int(background_color[3:5], 16)
    b = int(background_color[5:7], 16)

    brightness = (r * 299 + g * 587 + b * 114) / 1000

    return "#000000" if brightness > 128 else "#FFFFFF"


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(error="Too many requests. Please try again later."), 429


@app.route("/generate_image", methods=["POST"])
def generate_image():
    data = request.json
    scheme = data["scheme"]
    birth_date = datetime.strptime(data["birth_date"], "%Y-%m-%d").date()
    name = data["name"]

    weeks_lived = calculate_weeks_lived(birth_date)
    img = create_life_weeks_image(weeks_lived, name, scheme)

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr = img_byte_arr.getvalue()

    filename = f"life_weeks_{scheme}.png"

    return jsonify(
        {"image": base64.b64encode(img_byte_arr).decode("utf-8"), "filename": filename}
    )


def calculate_weeks_lived(birth_date):
    today = datetime.now()
    days_lived = (today - birth_date).days
    weeks_lived = days_lived // 7
    return weeks_lived


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
