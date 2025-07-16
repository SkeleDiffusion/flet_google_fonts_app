import flet as ft
import requests
import re


def get_google_fonts_metadata():
    try:
        response = requests.get("https://fonts.google.com/metadata/fonts")
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def find_font_family(search_name, metadata=None):
    if metadata is None:
        metadata = get_google_fonts_metadata()

    if not metadata:
        return None

    search_name_lower = search_name.lower()
    family_list = metadata.get("familyMetadataList", [])

    for font_data in family_list:
        family_name = font_data.get("family", "")
        if family_name.lower() == search_name_lower:
            return family_name

    for font_data in family_list:
        family_name = font_data.get("family", "")
        if search_name_lower in family_name.lower():
            return family_name

    return None


def get_font_urls(family_name):
    correct_family_name = find_font_family(family_name)

    if not correct_family_name:
        return None

    css_url = f"https://fonts.googleapis.com/css2?family={correct_family_name.replace(' ', '+')}:wght@400;700&display=swap"

    try:
        response = requests.get(css_url)
        response.raise_for_status()
        css_content = response.text

        font_faces = []
        face_pattern = r"/\*\s*([^*]+?)\s*\*/\s*@font-face\s*\{([^}]+)\}"
        matches = re.findall(face_pattern, css_content, re.MULTILINE | re.DOTALL)

        for subset, font_face_content in matches:
            subset = subset.strip()
            weight_match = re.search(r"font-weight:\s*(\d+)", font_face_content)
            weight = weight_match.group(1) if weight_match else "400"
            style_match = re.search(r"font-style:\s*(\w+)", font_face_content)
            style = style_match.group(1) if style_match else "normal"
            url_match = re.search(r"src:\s*url\(([^)]+)\)", font_face_content)

            if url_match:
                url = url_match.group(1)
                format_type = (
                    "woff2" if ".woff2" in url else "woff" if ".woff" in url else "ttf"
                )
                font_faces.append(
                    {
                        "subset": subset,
                        "weight": weight,
                        "style": style,
                        "url": url,
                        "format": format_type,
                    }
                )

        url_pattern = r"src:\s*url\(([^)]+)\)"
        all_urls = re.findall(url_pattern, css_content)

        return {
            "family": family_name,
            "fonts": font_faces,
            "all_urls": list(set(all_urls)),
        }

    except requests.RequestException:
        return None


def show_font_options(family_name):
    font_data = get_font_urls(family_name)
    if not font_data:
        return
    return font_data


def list_available_fonts(limit=50):
    metadata = get_google_fonts_metadata()
    if not metadata:
        return []

    fonts = []
    family_list = metadata.get("familyMetadataList", [])

    for font_data in family_list:
        family_name = font_data.get("family", "")
        if family_name:
            fonts.append({"family": family_name, "display_name": family_name})

        if len(fonts) >= limit:
            break

    return fonts


def main(page: ft.Page):
    page.title = "Google Fonts Explorer"
    page.theme = ft.Theme()

    if page.fonts is None:
        page.fonts = {}

    page._preview_fonts = {}

    text_field = ft.TextField(
        label="Search fonts (e.g: japanese, sans, mono...)",
        expand=True,
        on_change=lambda e: filter_fonts(e.control.value),
    )
    status_text = ft.Text("Type to search fonts")
    font_list = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)

    def new_font(name):
        if not name.strip():
            status_text.value = "Please enter a font name"
            page.update()
            return

        status_text.value = f"Loading font: {name}..."
        page.update()

        try:
            font_data = get_font_urls(name)
            if (
                font_data
                and font_data.get("all_urls")
                and len(font_data["all_urls"]) > 0
            ):
                page.fonts = {name: font_data["all_urls"][0]}
                page.theme.font_family = name
                status_text.value = f"Font applied: {name}"
                show_font_options(name)
            else:
                status_text.value = f"Could not load font: {name}"
        except Exception as e:
            status_text.value = f"Error loading font: {str(e)}"

        page.update()

    def filter_fonts(search_term=""):
        if not search_term.strip():
            font_list.controls.clear()
            font_list.controls.append(
                ft.Text("Type something to search fonts...", italic=True)
            )
            page.update()
            return

        status_text.value = f"Searching fonts containing: {search_term}..."
        page.update()

        fonts = list_available_fonts(1000)
        search_lower = search_term.lower()

        filtered_fonts = [
            font for font in fonts if search_lower in font["family"].lower()
        ]

        font_list.controls.clear()

        if filtered_fonts:
            for font in filtered_fonts[:15]:
                font_key = (
                    f"preview_{font['family'].replace(' ', '_').replace('-', '_')}"
                )

                if font_key in page._preview_fonts:
                    list_tile = ft.ListTile(
                        title=ft.Text(
                            font["display_name"], size=16, font_family=font_key
                        ),
                        subtitle=ft.Text(
                            font["family"],
                            size=12,
                            color=ft.Colors.GREY_600,
                            font_family=font_key,
                        ),
                        on_click=lambda e, family=font["family"]: [
                            setattr(text_field, "value", family),
                            page.update(),
                        ],
                    )
                else:
                    list_tile = ft.ListTile(
                        title=ft.Text(font["display_name"], size=16),
                        subtitle=ft.Text(
                            font["family"], size=12, color=ft.Colors.GREY_600
                        ),
                        on_click=lambda e, family=font["family"]: [
                            setattr(text_field, "value", family),
                            page.update(),
                        ],
                    )

                font_list.controls.append(list_tile)

                def load_font_for_preview(font_data, tile, font_key):
                    def load_font():
                        try:
                            if font_key in page._preview_fonts:
                                return

                            font_info = get_font_urls(font_data["family"])
                            if font_info and font_info.get("all_urls"):
                                font_url = font_info["all_urls"][0]

                                def update_fonts():
                                    try:
                                        page._preview_fonts[font_key] = font_url
                                        page.fonts[font_key] = font_url

                                        tile.title = ft.Text(
                                            font_data["display_name"],
                                            font_family=font_key,
                                            size=16,
                                        )
                                        tile.subtitle = ft.Text(
                                            font_data["family"],
                                            font_family=font_key,
                                            size=12,
                                            color=ft.Colors.GREY_600,
                                        )
                                        page.update()
                                    except Exception:
                                        pass

                                update_fonts()

                        except Exception:
                            pass

                    return load_font

                if font_key not in page._preview_fonts:
                    page.run_thread(load_font_for_preview(font, list_tile, font_key))

            status_text.value = f"Found {len(filtered_fonts)} fonts (showing {min(15, len(filtered_fonts))})"
        else:
            font_list.controls.append(
                ft.Text(f"No fonts found containing: {search_term}", italic=True)
            )
            status_text.value = "No fonts found"

        page.update()

    set_button = ft.ElevatedButton(
        "Apply selected font", on_click=lambda _: new_font(text_field.value)
    )

    clear_button = ft.ElevatedButton(
        "Clear search",
        on_click=lambda _: [
            setattr(text_field, "value", ""),
            filter_fonts(""),
            page.update(),
        ],
    )

    page.add(
        ft.Column(
            [
                ft.Text("Google Fonts Explorer", size=24, weight=ft.FontWeight.BOLD),
                ft.Row([text_field, set_button]),
                ft.Row([clear_button]),
                status_text,
                ft.Text("Search results:", weight=ft.FontWeight.BOLD),
                font_list,
            ]
        )
    )

    filter_fonts("")


ft.app(main, assets_dir="assets")
