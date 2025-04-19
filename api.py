# import math
# import itertools
# import json # For request body check
# from flask import Flask, request, jsonify # Removed render_template as not used in API part
# # Import serverless_wsgi to wrap the app
# import serverless_wsgi

# app = Flask(__name__)

# # --- Data Definitions (Same as before) ---
# PRODUCTS = {
#     "A": {"center": "C1", "weight": 3.0}, "B": {"center": "C1", "weight": 2.0},
#     "C": {"center": "C1", "weight": 8.0}, "D": {"center": "C2", "weight": 12.0},
#     "E": {"center": "C2", "weight": 25.0}, "F": {"center": "C2", "weight": 15.0},
#     "G": {"center": "C3", "weight": 0.5}, "H": {"center": "C3", "weight": 1.0},
#     "I": {"center": "C3", "weight": 2.0},
# }
# DISTANCES = {
#     ("C1", "L1"): 3.0, ("L1", "C1"): 3.0, ("C2", "L1"): 2.5, ("L1", "C2"): 2.5,
#     ("C3", "L1"): 2.0, ("L1", "C3"): 2.0, ("C1", "C2"): 4.0, ("C2", "C1"): 4.0,
#     ("C2", "C3"): 3.0, ("C3", "C2"): 3.0,
# }
# CENTERS = ["C1", "C2", "C3"]
# LOCATIONS = ["C1", "C2", "C3", "L1"]
# # Small epsilon for float comparisons
# EPSILON = 1e-9

# # --- Helper Functions (Slightly improved cost calculation clarity) ---
# def get_distance(loc1, loc2):
#     if loc1 == loc2: return 0.0
#     # Check both directions directly
#     dist = DISTANCES.get((loc1, loc2))
#     if dist is None: dist = DISTANCES.get((loc2, loc1))
#     # Return distance or infinity if not found
#     return dist if dist is not None else float('inf')

# def calculate_segment_cost(weight, distance):
#     if distance <= 0 or distance == float('inf'):
#         return 0.0 # No cost for zero or infinite distance travel

#     if weight <= EPSILON: # Treat near-zero weight as deadhead
#         cost_per_unit = 10.0
#     elif weight <= 5.0 + EPSILON:
#         cost_per_unit = 10.0
#     else:
#         # Calculate blocks needed *beyond* the initial 5kg block
#         additional_weight = max(0.0, weight - 5.0 - EPSILON)
#         additional_blocks = math.ceil(additional_weight / 5.0)
#         cost_per_unit = 10.0 + 8.0 * additional_blocks

#     return cost_per_unit * distance

# def _calculate_travel_cost_between_stops(loc_a, loc_b, weight_carried):
#     # Direct path cost
#     direct_dist = get_distance(loc_a, loc_b)
#     cost_direct = calculate_segment_cost(weight_carried, direct_dist)

#     # Indirect path via C2 (specifically for C1 <-> C3)
#     cost_indirect = float('inf')
#     if (loc_a, loc_b) in [("C1", "C3"), ("C3", "C1")]:
#         # Check if C2 is reachable from both ends
#         dist_a_c2 = get_distance(loc_a, "C2")
#         dist_c2_b = get_distance("C2", loc_b)

#         if dist_a_c2 != float('inf') and dist_c2_b != float('inf'):
#             cost_a_c2 = calculate_segment_cost(weight_carried, dist_a_c2)
#             cost_c2_b = calculate_segment_cost(weight_carried, dist_c2_b)
#             cost_indirect = cost_a_c2 + cost_c2_b

#     # Return the minimum valid cost (direct might be infinity)
#     return min(cost_direct, cost_indirect)


# # --- Core Calculation Logic (_calculate_overall_minimum_cost - Mostly same) ---
# def _calculate_overall_minimum_cost(order_data):
#     items_needed = order_data
#     if not items_needed:
#         return 0, None

#     needed_centers = set()
#     weight_from_center = {c: 0.0 for c in CENTERS}
#     total_weight = 0.0

#     for product_code, quantity in items_needed.items():
#         product_info = PRODUCTS[product_code]
#         center = product_info["center"]
#         weight = product_info["weight"]
#         item_total_weight = weight * quantity
#         needed_centers.add(center)
#         weight_from_center[center] += item_total_weight
#         total_weight += item_total_weight

#     min_overall_cost = float('inf')

#     for start_center in CENTERS:
#         cost_simple = float('inf')
#         pickup_centers_to_visit = list(needed_centers - {start_center})

#         # 🚚 STRATEGY 1: Simple (pick all first)
#         if not pickup_centers_to_visit:
#             if start_center in needed_centers:
#                 cost_simple = _calculate_travel_cost_between_stops(start_center, 'L1', total_weight)
#         else:
#             min_perm_cost = float('inf')
#             for order in itertools.permutations(pickup_centers_to_visit):
#                 current_perm_cost = 0.0
#                 current_weight = weight_from_center.get(start_center, 0.0)
#                 loc_a = start_center
#                 valid_path = True

#                 for loc_b in order:
#                     segment_cost = _calculate_travel_cost_between_stops(loc_a, loc_b, current_weight)
#                     if segment_cost == float('inf'):
#                         valid_path = False
#                         break
#                     current_perm_cost += segment_cost
#                     current_weight += weight_from_center.get(loc_b, 0.0)
#                     loc_a = loc_b

#                 if not valid_path:
#                     continue

#                 final_leg_cost = _calculate_travel_cost_between_stops(loc_a, 'L1', current_weight)
#                 if final_leg_cost == float('inf'):
#                     continue

#                 total_cost = current_perm_cost + final_leg_cost
#                 min_perm_cost = min(min_perm_cost, total_cost)

#             cost_simple = min_perm_cost

#         # 🚚 STRATEGY 2: Partial (drop-off after first center, then pick again)
#         cost_partial = float('inf')
#         if weight_from_center[start_center] > EPSILON and len(needed_centers) > 1:
#             weight_leg1 = weight_from_center[start_center]
#             cost_leg1 = _calculate_travel_cost_between_stops(start_center, "L1", weight_leg1)

#             if cost_leg1 != float('inf'):
#                 remaining_centers = list(needed_centers - {start_center})
#                 weight_remaining = total_weight - weight_leg1
#                 min_perm_pickup_cost = float('inf')

#                 for order in itertools.permutations(remaining_centers):
#                     current_cost = 0.0
#                     current_weight = 0.0
#                     loc_a = "L1"
#                     valid_path = True

#                     for loc_b in order:
#                         segment_cost = _calculate_travel_cost_between_stops(loc_a, loc_b, current_weight)
#                         if segment_cost == float('inf'):
#                             valid_path = False
#                             break
#                         current_cost += segment_cost
#                         current_weight += weight_from_center.get(loc_b, 0.0)
#                         loc_a = loc_b

#                     if not valid_path:
#                         continue

#                     final_leg_cost = _calculate_travel_cost_between_stops(loc_a, "L1", current_weight)
#                     if final_leg_cost == float('inf'):
#                         continue

#                     total_cost = current_cost + final_leg_cost
#                     min_perm_pickup_cost = min(min_perm_pickup_cost, total_cost)

#                 if min_perm_pickup_cost != float('inf'):
#                     cost_partial = cost_leg1 + min_perm_pickup_cost

#         min_overall_cost = min(min_overall_cost, cost_simple, cost_partial)

#     if min_overall_cost == float('inf'):
#         return None, "No valid delivery path found for the given order."

#     return round(min_overall_cost), None


# # --- Flask Routes ---

# # IMPORTANT: This single route '/' will handle POST requests routed to the function.
# # Netlify rewrites (in netlify.toml) will map a user-facing path (e.g., /api/calculate)
# # to this function's root.
# @app.route('/', methods=['POST'])
# def handle_calculate():
#     """ Handles POST requests for calculating the minimum delivery cost. """
#     # 1. Check Content-Type
#     content_type = request.headers.get('Content-Type')
#     if not content_type or 'application/json' not in content_type.lower():
#          return jsonify({"error": "Request Content-Type must be application/json"}), 415

#     # 2. Get and Validate JSON Body
#     try:
#         order_data = request.get_json()
#         if order_data is None: # Handles empty body or non-JSON parse result
#              raise ValueError("No JSON body found or failed to parse.") # Use ValueError for clarity
#     except Exception as e: # Catch JSONDecodeError and other potential issues
#         return jsonify({"error": f"Invalid JSON data in request body: {str(e)}"}), 400

#     # 3. Validate JSON Structure (must be an object/dict)
#     if not isinstance(order_data, dict):
#          return jsonify({"error": "Request JSON data must be an object (key-value pairs)."}), 400

#     # 4. Validate Order Items (Product Codes and Quantities)
#     validated_order = {}
#     validation_errors = []
#     for product_code, quantity in order_data.items():
#         # Ensure product code is a string (JSON keys are always strings)
#         if not isinstance(product_code, str):
#              validation_errors.append(f"Invalid product code format: {product_code}. Must be a string.")
#              continue # Skip further checks for this item

#         if product_code not in PRODUCTS:
#             validation_errors.append(f"Product code '{product_code}' not found.")
#             continue # Skip quantity check if product doesn't exist

#         if not isinstance(quantity, int):
#              validation_errors.append(f"Invalid quantity for {product_code}: '{quantity}'. Must be an integer.")
#         elif quantity < 0:
#              validation_errors.append(f"Invalid quantity for {product_code}: {quantity}. Cannot be negative.")
#         elif quantity > 0:
#              validated_order[product_code] = quantity # Only add items with quantity > 0

#     if validation_errors:
#         # Return a single error message with all validation failures
#         return jsonify({"error": "Order validation failed.", "details": validation_errors}), 400

#     # 5. Handle Empty Validated Order (all quantities were 0 or invalid)
#     if not validated_order:
#         return jsonify({"minimum_cost": 0}), 200 # No cost if no valid items ordered

#     # 6. Call the Core Calculation Logic
#     cost, error_msg = _calculate_overall_minimum_cost(validated_order)

#     # 7. Return Result or Error
#     if error_msg:
#         # Use 400 for calculation errors like "no path found" as it stems from the request input
#         return jsonify({"error": error_msg}), 400
#     else:
#         return jsonify({"minimum_cost": cost}), 200

# # Optional: Add a simple GET handler for the root for basic "is it alive?" checks
# @app.route('/', methods=['GET'])
# def handle_root_get():
#     """ Basic health check endpoint. """
#     return jsonify({"message": "Logistics Cost API Function is running. Use POST to calculate costs."}), 200

# # --- Serverless Handler ---
# # This is the entry point for Netlify Functions (AWS Lambda)
# def handler(event, context):
#     """
#     AWS Lambda handler function that integrates with Flask using serverless-wsgi.
#     """
#     # Use serverless_wsgi to translate the Lambda event/context into a WSGI request
#     # and call the Flask app (`app`) to handle it.
#     return serverless_wsgi.handle(app, event, context)

# # DO NOT INCLUDE app.run() for serverless deployment
# # if __name__ == '__main__':
# #     app.run(debug=True) # Only for local development testing







import math
import itertools
from flask import Flask, request, jsonify

app = Flask(__name__)

PRODUCTS = {
    "A": {"center": "C1", "weight": 3.0}, "B": {"center": "C1", "weight": 2.0}, "C": {"center": "C1", "weight": 8.0},
    "D": {"center": "C2", "weight": 12.0}, "E": {"center": "C2", "weight": 25.0}, "F": {"center": "C2", "weight": 15.0},
    "G": {"center": "C3", "weight": 0.5}, "H": {"center": "C3", "weight": 1.0}, "I": {"center": "C3", "weight": 2.0}
}

DISTANCES = {
    ("C1", "L1"): 3.0, ("L1", "C1"): 3.0,
    ("C2", "L1"): 2.5, ("L1", "C2"): 2.5,
    ("C3", "L1"): 2.0, ("L1", "C3"): 2.0,
    ("C1", "C2"): 4.0, ("C2", "C1"): 4.0,
    ("C2", "C3"): 3.0, ("C3", "C2"): 3.0
}

CENTERS = ["C1", "C2", "C3"]
EPSILON = 1e-9

def get_distance(loc1, loc2):
    if loc1 == loc2:
        return 0.0
    return DISTANCES.get((loc1, loc2), DISTANCES.get((loc2, loc1), float('inf')))

def calculate_segment_cost(weight, distance):
    if distance <= 0 or distance == float('inf'):
        return 0.0
    if weight <= EPSILON:
        cost_per_km = 10
    elif weight <= 5 + EPSILON:
        cost_per_km = 10
    else:
        extra = math.ceil((weight - 5) / 5)
        cost_per_km = 10 + (8 * extra)
    return cost_per_km * distance

def generate_all_routes(centers):
    """Generate all center permutations and all drop positions (L1 insertions)."""
    routes = []
    for perm in itertools.permutations(centers):
        n = len(perm)
        for drop_indices in range(1, n+1):  # Insert L1 once after 1 to n centers
            route = []
            for i in range(n):
                route.append(perm[i])
                if i + 1 == drop_indices:
                    route.append("L1")
            if route[-1] != "L1":
                route.append("L1")
            routes.append(route)
    return routes

def calculate_cost_for_route(route, weight_from_center):
    carried_weight = 0.0
    cost = 0.0
    picked_centers = set()
    loc_from = route[0]

    if loc_from == "L1":
        return float('inf')  # Can't start from L1

    if loc_from in CENTERS:
        carried_weight += weight_from_center[loc_from]
        picked_centers.add(loc_from)

    for loc_to in route[1:]:
        dist = get_distance(loc_from, loc_to)
        cost += calculate_segment_cost(carried_weight, dist)

        if loc_to == "L1":
            carried_weight = 0.0  # Delivered everything
        elif loc_to in CENTERS and loc_to not in picked_centers:
            carried_weight += weight_from_center[loc_to]
            picked_centers.add(loc_to)

        loc_from = loc_to

    return cost

def _calculate_overall_minimum_cost(order_data):
    involved_centers = set()
    weight_from_center = {c: 0.0 for c in CENTERS}

    for product, qty in order_data.items():
        if qty <= 0 or product not in PRODUCTS:
            continue
        center = PRODUCTS[product]["center"]
        weight = PRODUCTS[product]["weight"] * qty
        weight_from_center[center] += weight
        involved_centers.add(center)

    if not involved_centers:
        return 0, None

    all_routes = generate_all_routes(list(involved_centers))

    min_cost = float('inf')
    for route in all_routes:
        cost = calculate_cost_for_route(route, weight_from_center)
        min_cost = min(min_cost, cost)

    if min_cost == float('inf'):
        return None, "No valid delivery route found"
    return round(min_cost), None

@app.route("/", methods=["POST"])
def calculate_cost():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    order = request.get_json()
    if not isinstance(order, dict):
        return jsonify({"error": "Request must be a JSON object with product quantities"}), 400

    validated_order = {}
    for product, qty in order.items():
        if product not in PRODUCTS:
            continue
        if isinstance(qty, int) and qty > 0:
            validated_order[product] = qty

    if not validated_order:
        return jsonify({"minimum_cost": 0}), 200

    cost, error = _calculate_overall_minimum_cost(validated_order)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"minimum_cost": cost}), 200

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"message": "API is up"}), 200
