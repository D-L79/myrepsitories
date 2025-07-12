
from flask import Flask, render_template, request
import requests
import json
import logging

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
# Set up basic logging to see requests and errors in the console
logging.basicConfig(level=logging.INFO)

# API constants for the data.gov.il service
API_URL = "https://data.gov.il/api/3/action/datastore_search"
# This is the specific ID for the Israeli vehicle registry dataset
RESOURCE_ID = "053cea08-09bc-40ec-8f7a-156f0677aff3"


# --- Helper Function ---
def fetch_car_data(plate_number):
    """
    Fetches specific car data from the government database using an exact license plate number.

    :param plate_number: The full 8-digit license plate number.
    :return: A dictionary with the car's data or raises an exception on failure.
    :raises requests.exceptions.RequestException: For network-related errors.
    :raises ValueError: If the API response is unsuccessful, empty, or malformed.
    """
    logging.info(f"Fetching data for license plate: {plate_number}")

    # The API uses a 'filters' parameter for exact matching, which is more efficient.
    # The filter requires the plate number to be an integer.
    filters = json.dumps({"mispar_rechev": int(plate_number)})

    try:
        # Sending a POST request with the filters
        response = requests.post(
            API_URL,
            data={
                "resource_id": RESOURCE_ID,
                "filters": filters
            }
        )
        # This will raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()
        data = response.json()

        # Check if the request was successful and if any records were returned
        if data.get('success') and data['result'].get('records'):
            record = data['result']['records'][0]
            
            # Map the API's field names to user-friendly Hebrew names.
            # Using .get() provides a default value 'לא ידוע' if a field is missing.
            return {
                "תוצרת": record.get("tozeret_nm", "לא ידוע"),
                "דגם": record.get("kinuy_mishari", "לא ידוע"),
                "שנת יצור": record.get("shnat_yitzur", "לא ידוע"),
                "צבע": record.get("tzeva_rechev", "לא ידוע"),
                "סוג בעלות": record.get("baalut", "לא ידוע"),
                "סוג רכב": record.get("sug_degem", "לא ידוע"),
                "תאריך עלייה לכביש": record.get("moed_aliya_lakvish", "לא ידוע"),
                "נפח מנוע": record.get("nefach_manoa", "לא ידוע"),
                "מספר שלדה": record.get("misgeret", "לא ידוע"),
                "רמת גימור": record.get("ramat_gimur", "לא ידוע"),
            }
        else:
            # This case handles when the API call is successful but finds no car
            logging.warning(f"API returned success but no records for plate: {plate_number}")
            raise ValueError("הרכב לא נמצא במאגר המידע הממשלתי.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error communicating with API: {e}")
        raise requests.exceptions.RequestException("שגיאת תקשורת עם השרת הממשלתי. נסו שוב מאוחר יותר.")
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from API response. Response text: {response.text}")
        raise ValueError("התקבלה תגובה לא תקינה מהשרת.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in fetch_car_data: {e}")
        raise Exception(f"אירעה שגיאה בלתי צפויה: {e}")


# --- Main Application Route ---
@app.route('/', methods=['GET', 'POST'])
def index():
    car_info = None
    error = None
    plate_number_input = ''

    if request.method == 'POST':
        plate_number_input = request.form.get('plate', '').strip()

        # --- Input Validation ---
        if not plate_number_input:
            error = "חובה להזין מספר רישוי."
        elif not plate_number_input.isdigit():
            error = "מספר הרישוי יכול להכיל ספרות בלבד."
        elif len(plate_number_input) != 8:
            error = "יש להזין מספר רישוי מלא בעל 8 ספרות."
        else:
            # If input is valid, try to fetch the data
            try:
                car_info = fetch_car_data(plate_number_input)
            except Exception as e:
                # Catch any exception from the fetch function and display it to the user
                error = str(e)

    # Render the HTML page and pass the variables to it
    return render_template('index.html',
                           car_info=car_info,
                           error=error,
                           plate=plate_number_input)


# --- Run the Application ---
if __name__ == '__main__':
    # When running locally, debug=True is useful for development.
    # The port will be assigned automatically when run in many cloud environments.
    app.run(debug=True)
