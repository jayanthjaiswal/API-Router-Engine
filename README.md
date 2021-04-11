# API-Router-Engine

## Strategy Pattern & Dependency Injection

* Vendor and RouterEngine Class
* Vendor has state for traffic quota, availability and stats
* Router engine has state of vendor list and route strategy
* Different strategies for routing injected during runtime
as method
* Same set of checkpoint and recalculation functions works
around those strategies, keeping same behaviour intact
but with different intent
* Decorators can be added for checkpointing and
book-keeping

## Simulation

```python
self.run(): 
  
  self.set_vendor_availability():
    for vendor in vendor_list:
      for each row in opened vendor csv:
        vendor.is_available = row[‘API Available’]
  
  self.cater_request_output():
    for row in opened request time csv:
      ans = self.route(row)
      write ans['Request Index', 'Vendors tried'] in output csv
``` 

## Strategies

* Dummy Route : Route all request to vendor1
Some requests are never fulfilled, when vendor1 is down
* Simple Route: Route request to vendor1, if it is up, else to vendor2 and then, to vendor3 in order
All requests are fulfilled but the request tries the order
* Steady State Traffic Route : Route request based on steady state traffic quota only
* Dynamic Traffic Route: Routing request based on dynamic traffic quota based on failure & comeback

 ## Dynamic Traffic Route Algorithm
 
```python
def route_dynamic_traffic:
  a = get_index_multinomial_single_roll(traffic_prob_list) 
  for vendor in self.vendors_list[a:]:
    vendor_tried_list.append(vendor.label) 
    self.checkpoint_till_time_sec(vendor, time_sec) 
    if vendor.is_available[time_min - 1]:
      heappush(vendor.stats['success'], time_sec) 
      write_row['Vendors tried'] = '|'.join(vendor_tried_list) 
      break
    else:
      heappush(vendor.stats['failure'], time_sec)
  traffic_prob_list = self.recalculate_traffic_prob(time_sec) 
  return write_row
```




 
