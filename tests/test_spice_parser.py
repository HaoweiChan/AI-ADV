from tools.spice_parser import SpiceParser
import os

def test_parser():
    print("Testing Golden SCS Parser...")
    # Update path to use data/golden.scs which exists in the project
    test_file = "data/golden.scs"
    if not os.path.exists(test_file):
        print(f"Skipping test: {test_file} not found")
        return

    parser = SpiceParser(test_file)
    
    # Test TOP extraction
    # The golden.scs in data/ might use different cell names than test_data/golden.scs in adv_agent
    # Let's check data/golden.scs content:
    # //Cell Name: TOP
    top_content = parser.get_subckt_content("TOP")
    if top_content:
        print("Found TOP content.")
        # Test identifying model of an instance with parentheses
        # I_ADC (vin mid_node) ADC_GEN1
        model = parser.find_model_of_instance(top_content, "I_ADC")
        print(f"Model for I_ADC: {model} (Expected: ADC_GEN1)")
        if model == "ADC_GEN1":
             print("PASS: Correctly identified model from spectre syntax.")
        else:
             print("FAIL: Incorrect model identification.")
    else:
        print("FAIL: Could not find TOP block.")

    # Test AMP_CORE extraction
    # //Cell Name: AMP_CORE
    amp_content = parser.get_subckt_content("AMP_CORE")
    if amp_content:
        print("\nFound AMP_CORE content.")
        # Test simple M1
        # M1 (outp inp 0 0) NMOS w=1u l=0.1u
        model = parser.find_model_of_instance(amp_content, "M1")
        print(f"Model for M1: {model} (Expected: NMOS)")
        if model == "NMOS":
             print("PASS: Correctly identified primitive model.")
        else:
             print("FAIL: Incorrect primitive model identification.")
    else:
        print("FAIL: Could not find AMP_CORE block.")

if __name__ == "__main__":
    test_parser()

