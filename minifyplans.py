import json

def minify_plans(input_file="plans.json", output_file="plans_optimized.json"):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    lightweight_data = {"combos": []}

    for combo in data.get("combos", []):
        light_combo = {
            "id": combo["id"],
            "picking_order": combo["picking_order"],
            "sections": []
        }
        
        for sec in combo["sections"]:
            # Only keep the minimum required signature
            light_sec = {
                "code": sec.get("code"),
                "slots": sec.get("slots", "—"),
                "professor": sec.get("professor", "—"),
                "is_blank": sec.get("is_blank", False)
            }
            light_combo["sections"].append(light_sec)
            
        lightweight_data["combos"].append(light_combo)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(lightweight_data, f, indent=4)
        
    print(f"Success! Lightweight plans saved to {output_file}.")

if __name__ == "__main__":
    minify_plans()