from sys import argv
import sys
import os
import pandas as pd
from subprocess import call

"""
Values:
permit type
permit issued to
facility name
facility address
facility contact
facility description
federally enforceable conditions

## emission information
## if page with "Facility Permissible Emissions" exists then need:
name of pollutant  # written as "Name:"
potential to emit  # written as "PTE:" or "PTE(s):" and followed by value 

## "Emission Unit Permissible Emissions"
## if page with "Emission Unit Permissible Emissions" exists then need:
emission unit  # this should match up with the same emission unit and related information in subsequent pages below
name of pollutant  # written as "Name:"
potential to emit  # written as "PTE:" or "PTE(s):" and followed by value 

## in all subsequent pages 
## information on emission units, the equipment that releases pollution into the air 

emission units  # written as "Emission Unit: [unit id here]"
emission unit description  # written as "Emission Unit Description: [description here] and follows the above
control type  # written as "Control Type:" and not always present, depends on emission unit and may repeat multiple times, we only need it once 

## information on monitoring requirements 

monitoring type  # written as "Monitoring Type:"
monitoring frequency  # written as "Monitoring Frequency:"
parameter monitored  # written as "Parameter Monitored:" and not always present, it depends on monitoring type
upper permit limit  # written as "Upper Permit Limit:" and not always present, depends on monitoring type
lower permit limit  # written as "Lower Permit Limit:" and not always present, depends on monitoring type
"""


def convert(pdf):
    call(["pdftotext", "-layout", pdf])


def clean(name_text):
    to_parse = []
    with open(name_text) as f:
        for line in f:
            line = line.decode("ascii", "ignore")
            line = line.replace("\n", "")
            line = line.replace("\t", "")
            if line != '':
                to_parse.append(line)
    return to_parse


def background_segment(cleaned):
    records = []
    record = []
    start = False
    for ind, line in enumerate(cleaned):
        first = "Permit Type" in line
        if first:
            start = True
        if start:
            record.append(line)
            if "Permit Type:" in line:
                permit_type = line.split("Permit Type:")[1]
                values["permit_type"].append(str(permit_type).strip())
            if "Facility DEC ID:" in line:
                dec_id = line.split("Facility DEC ID:")[1]
                values["dec_id"].append(str(dec_id).strip())
            if "Permit Issued To:" in line:
                permit_issued = line.split("Permit Issued To:")[1]
                values["permit_issued_to"].append(str(permit_issued).strip())
            if "Facility:" in line:
                facility_name = line.split("Facility:")[1]
                values["facility_name"].append(str(facility_name).strip())

                facility_street = cleaned[ind+1]
                values["facility_street"].append(str(facility_street).strip())
                facility_city = cleaned[ind+2].split(",")[0]
                values["facility_city"].append(str(facility_city).strip())
                facility_zip = cleaned[ind+2].split(",")[1][3:]
                values["facility_zip"].append(str(facility_zip).strip())
            if "Contact:" in line:
                facility_contact = line.split("Contact:")[1]
                values["facility_contact"].append(str(facility_contact).strip())

            first = "By acceptance of this permit" in line
            if first:
                records.append(record)
                record = []
                start = False


    return records


def list_of_conditions_segment(cleaned):
    records = []
    record = []
    start = False
    for ind, line in enumerate(cleaned):
        first = "FEDERALLY ENFORCEABLE CONDITIONS" in line
        if first:
            start = True
        if start:
            record.append(line)
            if "40CFR 63" in line:
                facility_mact = line.split("Subpart")[1]
                mact_val = str(facility_mact).strip()
                if mact_val not in values["facility_mact"] and len(mact_val) < 8:
                    values["facility_mact"].append(mact_val)
            if "40CFR 60" in line:
                facility_nsps = line.split("Subpart")[1]
                nsps_val = str(facility_nsps).strip()
                if nsps_val not in values["facility_nsps"] and len(nsps_val) < 8:
                    values["facility_nsps"].append(nsps_val)

            first = "STATE ONLY ENFORCEABLE CONDITIONS" in line
            if first:
                records.append(record)
                record = []
                start = False
    return records


def rest_of_file_segment(cleaned):
    records = []
    record = []
    start = False

    for ind, line in enumerate(cleaned):
        first = "Emission Unit:" in line
        if first:
            start = True
        if start:
            records.append(line)
    return records


def emission_parse(record):
    in_range = True
    in_range_plus_ten = True

    for ind, line in enumerate(record):
        name_exists = False
        PTE_exists = False

        if "Emission Unit:" in line:
            try:
                record[ind+1]
            except IndexError:
                in_range = False
            if in_range:
                # Get all emission units
                emission_unit_line = str(line.split("Emission Unit:")[1]).strip()
                emission_unit = emission_unit_line.split(" ")[0]
                if emission_unit not in values["emission_unit"] and emission_unit != '':
                    values["emission_unit"].append(str(emission_unit).strip())

                if "Process Description" in record[ind + 1]:
                    values["process_description"].append(
                        [record[ind + 1].split("Process Description")[1], emission_unit])
                else:
                    continue
                if "Emission Unit Description" in record[ind + 1]:
                    values["emission_unit_description"].append(
                        [record[ind + 1].split("Emission Unit Description")[1], emission_unit])
                else:
                    continue
                try:
                    record[ind + 10]
                except IndexError:
                    in_range_plus_ten = False
                if in_range_plus_ten:
                    for i in xrange(ind, ind + 11):
                        if "Name:" in record[i]:
                            values["pollutant"].append(record[i].split("Name:")[1])
                            name_exists = True
                        if "PTE" in record[i]:
                            new_line = record[i].replace("(", "")
                            new_line = new_line.replace("s", "")  # assumes name is upper case
                            new_line = new_line.replace(")", "")
                            values["potential_to_emit"].append(record[i].split("PTE")[1])
                            PTE_exists = True
                        if not name_exists:
                            continue
                        else:
                            name_exists = False
                        if not PTE_exists:
                            continue
                        else:
                            PTE_exists = False
                        # Get all controls

        if "Control Type:" in line:
            control_type = str(line.split("Control Type:")[1]).strip()
            if control_type not in values["control_type"] and control_type != '':
                values["control_type"].append(str(control_type).strip())

        if "Name:" in line:
            pollutant = str(line.split("Name:")[1]).strip()
            if pollutant not in values["pollutant"] and pollutant != '':
                values["pollutant"].append(str(pollutant).strip())

    return values


def main(pdf=None):
    if pdf == None:
        #pdf = sys.argv[1]
        pdf = '/Users/Steve/Github/ny_caa_permit_parser/914640016400117_r1_4.pdf'
        #pdf = '/Users/Steve/Github/ny_caa_permit_parser/552050000500059_r2.pdf'

    if "@" in pdf and pdf.count(".") == 2:
        name_text = pdf.split(".")[0] + "." + pdf.split(".")[1] + ".txt"
        name_csv = pdf.split(".")[0] + "." + pdf.split(".")[1] + ".csv"
    else:
        name_text = pdf.split(".")[0] + ".txt"
        name_csv = pdf.split(".")[0] + ".csv"

    if not os.path.exists(name_text):
        convert(pdf)
    records = []
    cleaned = clean(name_text)

    stuff_we_care_about = [background_segment(cleaned)+list_of_conditions_segment(cleaned)+rest_of_file_segment(cleaned)]

    for record in stuff_we_care_about:
        records.append(emission_parse(record))



    df = pd.DataFrame(columns=["permit_type",
                               "dec_id",
                               "permit_issued_to",
                               "facility_name",
                               "facility_street",
                               "facility_city",
                               "facility_zip",
                               "facility_contact",
                               "facility_description",
                               "facility_mact",
                               "facility_nsps",
                               "emission_unit",
                               "control_type",
                               "pollutant",
                               "potential_to_emit",
                               "emission_unit_description",
                               "process_description",
                               "monitoring_type",
                               "monitoring_frequency",
                               "parameter_monitored",
                               "upper_permit_limit",
                               "lower_permit_limit"])

    for record in records:
        df = df.append(record, ignore_index=True)
    df.to_csv(name_csv)


if __name__ == '__main__':
    values = {
        "permit_type": [],
        "dec_id": [],
        "permit_issued_to": [],
        "facility_name": [],
        "facility_street": [],
        "facility_city": [],
        "facility_zip": [],
        "facility_contact": [],
        "facility_mact": [],
        "facility_nsps": [],
        "emission_unit": [],
        "control_type": [],
        "pollutant": [],
        "potential_to_emit": [],
        "emission_unit_description": [],
        "process_description": []
    }

    main()

