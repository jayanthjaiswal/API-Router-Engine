import csv
import heapq
import types

import numpy as np

MAX_TIME_MIN = 300
VENDORS = list(map(lambda x: 'vendor{}'.format(x + 1), range(3)))
STEADY_STATE = {
    "vendor1": 80,
    "vendor2": 20,
    "vendor3": 0
}
X = 40
Y = 5
A = 80
B = 5

REQUEST_FILE = "data/request-time.csv"
OUTPUT_FILE = "output/output.csv"
MASTER_FILE = "output/master.csv"


def get_index_multinomial_single_roll(steady_state_traffic_p_list):
    roll_list = list(np.random.multinomial(1, steady_state_traffic_p_list))
    return roll_list.index(1)


class Vendor:
    def __init__(self, label, steady_state_traffic, x, y, a, b):
        self.label = label
        self.steady_state_traffic = steady_state_traffic
        self.traffic_p = steady_state_traffic / 100.0
        self.is_available = [True] * MAX_TIME_MIN
        self.is_down = [False] * MAX_TIME_MIN * 60
        self.failure_threshold = x
        self.failure_threshold_sec = y * 60
        self.comeback_threshold = a
        self.comeback_threshold_sec = b * 60
        self.request_stats_ftm = {'req_status_success': [], 'req_status_failure': []}
        self.request_stats_ctm = {'req_status_success': [], 'req_status_failure': []}

    def __str__(self):
        """Returns a human-readable string representation """
        return '{} having traffic probability {}'.format(self.label, self.traffic_p)


class RouterEngine:
    def __init__(self, vendors_list, func=None):
        self.vendors_list = vendors_list
        if func is not None:
            self.route = types.MethodType(func, self)

    def route(self, row):
        raise Exception("route not implemented yet. Please add a strategy.")

    def write_misc_columns_csv(self, time_min, time_sec, write_row, tm_output_percent=None):
        for current_vendor in self.vendors_list:
            write_row['Request Time (Seconds)'] = time_sec
            write_row['{} API Available'.format(current_vendor.label)] = current_vendor.is_available[time_min - 1]
            write_row['{} Is Down'.format(current_vendor.label)] = current_vendor.is_down[time_sec]
            write_row['{} FTM Failure Percent'.format(current_vendor.label)] = tm_output_percent[
                '{} FTM Failure Percent'.format(current_vendor.label)] if tm_output_percent else 0
            write_row['{} CTM Success Percent'.format(current_vendor.label)] = tm_output_percent[
                '{} CTM Success Percent'.format(current_vendor.label)] if tm_output_percent else 100
            write_row['{} Traffic Ratio'.format(current_vendor.label)] = current_vendor.traffic_p

    def recalculate_traffic_p(self, time_sec):
        tm_output_percent = {}
        carry_over = 0
        for each_vendor in self.vendors_list:

            ftm_success_count = len(each_vendor.request_stats_ftm['req_status_success'])
            ftm_failure_count = len(each_vendor.request_stats_ftm['req_status_failure'])
            ftm_total = ftm_success_count + ftm_failure_count
            if not ftm_total:
                ftm_failure_percent = 0
            else:
                ftm_failure_percent = ftm_failure_count * 100.0 / ftm_total

            ctm_success_count = len(each_vendor.request_stats_ctm['req_status_success'])
            ctm_failure_count = len(each_vendor.request_stats_ctm['req_status_failure'])
            ctm_total = ctm_success_count + ctm_failure_count
            if not ctm_total:
                ctm_success_percent = 100
            else:
                ctm_success_percent = ctm_success_count * 100.0 / ctm_total

            tm_output_percent['{} FTM Failure Percent'.format(each_vendor.label)] = ftm_failure_percent
            tm_output_percent['{} CTM Success Percent'.format(each_vendor.label)] = ctm_success_percent

            if ftm_failure_percent > each_vendor.failure_threshold:
                each_vendor.is_down[time_sec] = True
                each_vendor.traffic_p = (each_vendor.steady_state_traffic * .1) / 100.0
                carry_over += (each_vendor.steady_state_traffic * .9) / 100.0
            elif each_vendor.is_down[time_sec] and ctm_success_percent > each_vendor.comeback_threshold:
                each_vendor.is_down[time_sec] = False
                each_vendor.traffic_p = each_vendor.steady_state_traffic / 100.0
                each_vendor.traffic_p += carry_over
                carry_over = 0
            else:
                each_vendor.traffic_p = each_vendor.steady_state_traffic / 100.0
                each_vendor.traffic_p += carry_over
                carry_over = 0

        return tm_output_percent

    def checkpoint_till_time_sec(self, current_vendor, time_sec):
        while current_vendor.request_stats_ctm['req_status_success'] and time_sec - \
                current_vendor.request_stats_ctm['req_status_success'][0] >= current_vendor.comeback_threshold_sec:
            heapq.heappop(current_vendor.request_stats_ctm['req_status_success'])
        while current_vendor.request_stats_ctm['req_status_failure'] and time_sec - \
                current_vendor.request_stats_ctm['req_status_failure'][0] >= current_vendor.comeback_threshold_sec:
            heapq.heappop(current_vendor.request_stats_ctm['req_status_failure'])
        while current_vendor.request_stats_ftm['req_status_success'] and time_sec - \
                current_vendor.request_stats_ftm['req_status_success'][0] >= current_vendor.failure_threshold_sec:
            heapq.heappop(current_vendor.request_stats_ftm['req_status_success'])
        while current_vendor.request_stats_ftm['req_status_failure'] and time_sec - \
                current_vendor.request_stats_ftm['req_status_failure'][0] >= current_vendor.failure_threshold_sec:
            heapq.heappop(current_vendor.request_stats_ftm['req_status_failure'])

    def set_vendor_availability(self):
        for current_vendor in self.vendors_list:
            f = 'data/{}.csv'.format(current_vendor.label)
            with open(f) as vendor_csv_file_read:
                csv_file_dict_reader = csv.DictReader(vendor_csv_file_read)
                for row in csv_file_dict_reader:
                    # print(v, row['Time (Minutes)'], row['API Available'])
                    if row['API Available'] == "true":
                        current_vendor.is_available[int(row['Time (Minutes)'])] = True
                    else:
                        current_vendor.is_available[int(row['Time (Minutes)'])] = False

    def cater_request_output(self):
        with open(REQUEST_FILE) as request_csv_file_read:
            csv_file_dict_reader = csv.DictReader(request_csv_file_read)
            with open(MASTER_FILE, 'w') as master_csv_file_write:
                master_csv_file_dict_writer = csv.DictWriter(master_csv_file_write,
                                                             fieldnames=['Request Index',
                                                                         'Request Time (Seconds)',
                                                                         'vendor1 API Available',
                                                                         'vendor2 API Available',
                                                                         'vendor3 API Available',
                                                                         'vendor1 Is Down',
                                                                         'vendor2 Is Down',
                                                                         'vendor3 Is Down',
                                                                         'vendor1 CTM Success Percent',
                                                                         'vendor2 CTM Success Percent',
                                                                         'vendor3 CTM Success Percent',
                                                                         'vendor1 FTM Failure Percent',
                                                                         'vendor2 FTM Failure Percent',
                                                                         'vendor3 FTM Failure Percent',
                                                                         'vendor1 Traffic Ratio',
                                                                         'vendor2 Traffic Ratio',
                                                                         'vendor3 Traffic Ratio',
                                                                         'Vendors tried'])
                master_csv_file_dict_writer.writeheader()
                with open(OUTPUT_FILE, 'w') as request_csv_file_write:
                    csv_file_dict_writer = csv.DictWriter(request_csv_file_write, fieldnames=
                    ['Request Index', 'Vendors tried'])
                    csv_file_dict_writer.writeheader()
                    for row in csv_file_dict_reader:
                        write_row_master = self.route(row)
                        write_row = {key: write_row_master[key] for key in write_row_master.keys() &
                                     {'Request Index', 'Vendors tried'}}
                        csv_file_dict_writer.writerow(write_row)
                        master_csv_file_dict_writer.writerow(write_row_master)

    def run(self):
        self.set_vendor_availability()
        self.cater_request_output()


def route_dummy(self, row):
    # print('Routing request {} to vendor1'.format(row['Request Index']))
    time_sec = int(row['Request Time (Seconds)'])
    time_min = int((time_sec / 60.0) + 1)
    write_row = {'Request Index': row['Request Index'],
                 'Request Time (Seconds)': time_sec,
                 'Vendors tried': self.vendors_list[0].label
                 }
    for current_vendor in self.vendors_list:
        self.checkpoint_till_time_sec(current_vendor, time_sec)

    tm_output_percent = None

    self.write_misc_columns_csv(time_min, time_sec, write_row, tm_output_percent)

    return write_row


def route_simple(self, row):
    # print('Routing request {} to vendor1 if it is up else to vendor2'.format(row['Request Index']))
    time_sec = int(row['Request Time (Seconds)'])
    time_min = int((time_sec / 60.0) + 1)
    vendor_tried_list = []
    a = 0
    write_row = {'Request Index': row['Request Index'],
                 'Request Time (Seconds)': time_sec,
                 'Vendors tried': '|'.join(vendor_tried_list)
                 }
    for current_vendor in self.vendors_list[a:]:
        vendor_tried_list.append(current_vendor.label)
        self.checkpoint_till_time_sec(current_vendor, time_sec)
        if current_vendor.is_available[time_min - 1]:
            write_row['Vendors tried'] = '|'.join(vendor_tried_list)
            break

    tm_output_percent = None

    self.write_misc_columns_csv(time_min, time_sec, write_row, tm_output_percent)

    return write_row


def route_steady_state_traffic(self, row):
    # print('Routing request {} based on steady-state traffic quota ratio'.format(row['Request Index']))
    time_sec = int(row['Request Time (Seconds)'])
    time_min = int((time_sec / 60.0) + 1)
    vendor_tried_list = []
    steady_state_traffic_p_list = list(map(lambda x: x.traffic_p, self.vendors_list))
    a = get_index_multinomial_single_roll(steady_state_traffic_p_list)
    write_row = {'Request Index': row['Request Index'],
                 'Vendors tried': '|'.join(vendor_tried_list)
                 }
    for current_vendor in self.vendors_list[a:]:
        vendor_tried_list.append(current_vendor.label)
        self.checkpoint_till_time_sec(current_vendor, time_sec)
        if current_vendor.is_available[time_min - 1]:
            write_row['Vendors tried'] = '|'.join(vendor_tried_list)
            break

    tm_output_percent = None

    self.write_misc_columns_csv(time_min, time_sec, write_row, tm_output_percent)

    return write_row


def route_dynamic_traffic(self, row):
    # print('Routing request {} based on dynamic traffic ratio on failure & comeback'.format(row['Request Index']))
    time_sec = int(row['Request Time (Seconds)'])
    time_min = int((time_sec / 60.0) + 1)
    vendor_tried_list = []
    traffic_p_list = list(map(lambda x: x.traffic_p, self.vendors_list))
    a = get_index_multinomial_single_roll(traffic_p_list)
    write_row = {'Request Index': row['Request Index'],
                 'Vendors tried': '|'.join(vendor_tried_list)
                 }
    for current_vendor in self.vendors_list[a:]:
        vendor_tried_list.append(current_vendor.label)

        self.checkpoint_till_time_sec(current_vendor, time_sec)

        if current_vendor.is_available[time_min - 1]:
            heapq.heappush(current_vendor.request_stats_ftm['req_status_success'], time_sec)
            heapq.heappush(current_vendor.request_stats_ctm['req_status_success'], time_sec)
            write_row['Vendors tried'] = '|'.join(vendor_tried_list)
            break
        else:
            heapq.heappush(current_vendor.request_stats_ftm['req_status_failure'], time_sec)
            heapq.heappush(current_vendor.request_stats_ctm['req_status_failure'], time_sec)

    tm_output_percent = self.recalculate_traffic_p(time_sec)

    self.write_misc_columns_csv(time_min, time_sec, write_row, tm_output_percent)

    return write_row


if __name__ == '__main__':
    vendors = list(map(
        lambda x: Vendor(x, STEADY_STATE[x], X, Y, A, B), VENDORS))
    solution = RouterEngine(vendors, route_steady_state_traffic)
    solution.run()

#
