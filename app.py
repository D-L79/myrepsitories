# app.py
from flask import Flask, render_template, request
import requests
import logging
import json

# --- Configuration ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
SESSION = requests.Session()

# Resource IDs are now categorized by vehicle type
RESOURCES = {
    "car": "053cea08-09bc-40ec-8f7a-156f0677aff3",
    "motorcycle": "bf9df4e2-d90d-4c0a-a400-19e15af8e95f",
    "cme": "58dc4654-16b1-42ed-8170-98fadec153ea",
    "public": "cf29862d-ca25-4691-84f6-1be60dcb4a1e",
    "truck": "cd3acc5c-03c3-4c89-9c54-d40f93c0d790", # Trucks over 3.5 tons
    # Secondary databases
    "disabled_permit": "c8b9f9c8-4612-4068-934f-d4acd2e3c06e",
    "personal_import": "03adc637-b6fe-402b-9937-7c3d3afc9140",
    "recalls": "56063a99-8a3e-4ff4-912e-5966c0279bad"
}
API_URL = "https://data.gov.il/api/3/action/datastore_search"

# --- Helper Functions ---

def query_datastore_robust(resource_id, plate_number):
    """
    A more robust query function that uses a broad search ('q') and then
    validates the result for an exact match against multiple possible field names.
    """
    try:
        params = {'resource_id': resource_id, 'q': plate_number}
        response = SESSION.get(API_URL, params=params, timeout=7)
        response.raise_for_status()
        data = response.json()
        if data.get('success') and data['result'].get('records'):
            for record in data['result']['records']:
                if str(record.get('mispar_rechev')) == str(plate_number) or \
                   str(record.get('mispar_rishuy')) == str(plate_number) or \
                   str(record.get('mispar_tzama')) == str(plate_number):
                    return record
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        logging.error(f"API call failed for resource {resource_id} with plate {plate_number}: {e}")
    return None


def fetch_all_data(plate_number, vehicle_type):
    """
    Fetches data and builds a specific dictionary based on the vehicle type.
    """
    primary_resource_id = RESOURCES.get(vehicle_type)
    if not primary_resource_id:
        raise ValueError("סוג רכב לא תקין נשלח מהמערכת.")

    main_data_record = query_datastore_robust(primary_resource_id, plate_number)
    
    if not main_data_record:
        raise ValueError("לא הצלחנו לאתר את מספר הרישוי במאגר שנבחר. אנא ודא שהמספר והלשונית נכונים.")

    # --- Build a specific info dictionary for each vehicle type ---
    info = {}

    if vehicle_type == 'car':
        info.update({
            "מידע ראשי": {
                "מספר רכב": plate_number,
                "תוצרת": main_data_record.get("tozeret_nm", "לא ידוע"),
                "דגם": main_data_record.get("kinuy_mishari", "לא ידוע"),
                "שנת יצור": main_data_record.get("shnat_yitzur", "לא ידוע"),
                "צבע": main_data_record.get("tzeva_rechev", "לא ידוע"),
                "סוג בעלות": main_data_record.get("baalut", "לא ידוע"),
            },
            "מידע מורחב": {
                "רמת גימור": main_data_record.get("ramat_gimur", "לא ידוע"),
                "אבזור בטיחותי": main_data_record.get("ramat_eivzur_betihuty", "לא ידוע"),
                "קבוצת זיהום": main_data_record.get("kvutzat_zihum", "לא ידוע"),
                "סוג דלק": main_data_record.get("sug_delek_nm", "לא ידוע"),
                "תוקף טסט": main_data_record.get("tokef_dt", "לא ידוע"),
                "מספר שלדה": main_data_record.get("misgeret", "לא ידוע"),
            }
        })
    elif vehicle_type == 'motorcycle':
        info.update({
            "מידע ראשי": {
                "מספר רכב": plate_number,
                "תוצרת": main_data_record.get("tozeret_nm", "לא ידוע"),
                "דגם": main_data_record.get("kdegem_nm", "לא ידוע"),
                "שנת יצור": main_data_record.get("shnat_yitzur", "לא ידוע"),
                "נפח מנוע": main_data_record.get("nefach_manoa", "לא ידוע"),
                "צבע": main_data_record.get("tzeva_rechev", "לא ידוע"),
            },
            "מידע מורחב": {
                "סוג בעלות": main_data_record.get("baalut", "לא ידוע"),
                "סוג דלק": main_data_record.get("sug_delek_nm", "לא ידוע"),
                "תוקף טסט": main_data_record.get("tokef_dt", "לא ידוע"),
            }
        })
    elif vehicle_type == 'cme':
        info.update({
            "מידע ראשי": {
                "מספר רכב": plate_number,
                "תוצר": main_data_record.get("shilda_totzar_en_nm", "לא ידוע"),
                "סוג צמ\"ה": main_data_record.get("sug_tzama_nm", "לא ידוע"),
                "דגם": main_data_record.get("degem_nm", "לא ידוע"),
                "שנת יצור": main_data_record.get("shnat_yitzur", "לא ידוע"),
            },
            "מידע מורחב": {
                "משקל כולל": main_data_record.get("mishkal_kolel", "לא ידוע"),
                "הוראות רישום": main_data_record.get("horaat_rishum", "לא ידוע"),
                "מספר שלדה": main_data_record.get("mispar_shilda", "לא ידוע"),
                "תוקף רישיון": main_data_record.get("tokef_date", "לא ידוע"),
            }
        })
    elif vehicle_type == 'public':
        info.update({
            "מידע ראשי": {
                "מספר רכב": plate_number,
                "סוג רכב": main_data_record.get("sug_rechev_nm", "לא ידוע"),
                "תוצרת": main_data_record.get("tozeret_nm", "לא ידוע"),
                "דגם": main_data_record.get("degem_nm", "לא ידוע"),
                "שנת יצור": main_data_record.get("shnat_yitzur", "לא ידוע"),
            },
            "מידע מורחב": {
                "מקומות ישיבה": main_data_record.get("mispar_mekomot", "לא ידוע"),
                "ביטול רישיון": main_data_record.get("bitul_nm", "לא ידוע"),
                "תאריך ביטול": main_data_record.get("sbitul_dt", "לא ידוע"),
                "תוקף רישיון": main_data_record.get("tokef_dt", "לא ידוע"),
            }
        })
    elif vehicle_type == 'truck':
        info.update({
            "מידע ראשי": {
                "מספר רכב": plate_number,
                "תוצרת": main_data_record.get("tozeret_nm", "לא ידוע"),
                "דגם": main_data_record.get("kinuy_mishari", "לא ידוע"),
                "שנת יצור": main_data_record.get("shnat_yitzur", "לא ידוע"),
                "משקל כולל": main_data_record.get("mishkal_kolel", "לא ידוע"),
            },
            "מידע מורחב": {
                "צבע": main_data_record.get("tzeva_rechev", "לא ידוע"),
                "סוג דלק": main_data_record.get("sug_delek_nm", "לא ידוע"),
                "תוקף טסט": main_data_record.get("tokef_dt", "לא ידוע"),
                "מספר שלדה": main_data_record.get("misgeret", "לא ידוע"),
            }
        })

    # Add secondary checks to all types
    info["בדיקות נוספות"] = {
        "תג נכה": "לא קיים",
        "יבוא אישי": "לא",
        "סטטוס ריקול": "לא נמצאה הודעה"
    }
    if query_datastore_robust(RESOURCES["disabled_permit"], plate_number):
        info["בדיקות נוספות"]["תג נכה"] = "קיים"
    if query_datastore_robust(RESOURCES["personal_import"], plate_number):
        info["בדיקות נוספות"]["יבוא אישי"] = "כן"
    if query_datastore_robust(RESOURCES["recalls"], plate_number):
        info["בדיקות נוספות"]["סטטוס ריקול"] = "נמצאה הודעת ריקול פתוחה"

    return info


# --- Main Application Route ---
@app.route('/', methods=['GET', 'POST'])
def index():
    vehicle_data = None
    error = None
    plate_number_input = ''
    active_tab = 'car'

    if request.method == 'POST':
        plate_number_input = request.form.get('plate', '').strip()
        active_tab = request.form.get('vehicle_type', 'car')

        is_valid = False
        error_message = ""

        if active_tab == 'cme':
            if not plate_number_input.isdigit() or len(plate_number_input) < 3:
                error_message = "עבור צמ\"ה, יש להזין 3 ספרות לפחות."
            else:
                is_valid = True
        elif active_tab == 'truck': # ADDED: Validation for trucks
            if not plate_number_input.isdigit() or len(plate_number_input) < 4:
                error_message = "עבור משאיות, יש להזין 4 ספרות לפחות."
            else:
                is_valid = True
        else: # car, motorcycle, or public
            if not plate_number_input.isdigit() or not (6 <= len(plate_number_input) <= 8):
                error_message = "יש להזין מספר רישוי תקין בעל 6-8 ספרות."
            else:
                is_valid = True

        if not is_valid:
            error = error_message
        else:
            try:
                vehicle_data = fetch_all_data(plate_number_input, active_tab)
            except Exception as e:
                error = str(e)

    return render_template('index.html',
                           vehicle_data=vehicle_data,
                           error=error,
                           plate=plate_number_input,
                           active_tab=active_tab)


# --- Run the Application ---
if __name__ == '__main__':
    app.run(debug=True)
