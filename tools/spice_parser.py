import re
from typing import Dict, Optional, List

class SpiceParser:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.subckts: Dict[str, Dict[str, int]] = {}  # {name: {'start': line_num, 'end': line_num}}
        self.content_lines: List[str] = []
        self._load_and_index()
        self.debug = True

    def _load_and_index(self):
        """Loads the file into memory and indexes .subckt definitions."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.content_lines = f.readlines()
        except FileNotFoundError:
            print(f"Error: File not found at {self.filepath}")
            return

        current_subckt = None
        subckt_start_line = -1
        
        # Regex for finding Custom Comment Format (case insensitive)
        # Captures the subckt name. Handles lines like:
        # "// Cell name: MY_AMP", "// Cell name MY_AMP"
        # Group 1 will be the cell name (non-space string after optional colon)
        custom_start_pattern = re.compile(r'//\s*Cell name\s*:?\s*(\S+)', re.IGNORECASE)
        custom_end_pattern = re.compile(r'//\s*End of subcircuit definition', re.IGNORECASE)

        for i, line in enumerate(self.content_lines):
            # Check for Custom Comment subckt
            custom_start_match = custom_start_pattern.search(line)
            if custom_start_match:
                current_subckt = custom_start_match.group(1)
                subckt_start_line = i
                continue

            # Check for End
            # Note: We assume non-nested subckts for simplicity in this indexer
            if current_subckt:
                if custom_end_pattern.search(line):
                    self.subckts[current_subckt] = {
                        'start': subckt_start_line,
                        'end': i
                    }
                    current_subckt = None
        # === Hardcoded block for Cell name AAA (easy to remove) ===
        # If a line starts with // Cell name AAA, treat until next blank line as one subckt block.
        for i, line in enumerate(self.content_lines):
            custom_start_match = custom_start_pattern.search(line)
            if custom_start_match and custom_start_match.group(1) == "SIMTR_SB_TX":
                cell_name = "SIMTR_SB_TX"
                end_line = None
                for k in range(i + 1, len(self.content_lines)):
                    if self.content_lines[k].strip() == "":
                        end_line = k - 1
                        break
                if end_line is None:
                    end_line = len(self.content_lines) - 1
                self.subckts[cell_name] = {
                    'start': i,
                    'end': end_line
                }
        # === End hardcoded AAA block detection ===
    
        

    def get_subckt_content(self, subckt_name: str) -> Optional[str]:
        """Returns the full text content of a subckt definition."""
        if subckt_name not in self.subckts:
            return None
        
        indices = self.subckts[subckt_name]
        # Return lines including .subckt and .ends
        return "".join(self.content_lines[indices['start'] : indices['end'] + 1])

    def find_model_of_instance(self, subckt_content: str, instance_name: str) -> Optional[str]:
        """
        Parses a subckt content to find the model name used by a specific instance.
        
        Args:
            subckt_content: The text body of the parent subcircuit.
            instance_name: The name of the instance to look for (e.g., "X1", "M1").
            
        Returns:
            The name of the subcircuit/model instantiated by this instance.
        """
        # SPICE instance line format: Name Node1 Node2 ... ModelName [Params]
        # We need to find the line starting with instance_name
        # Note: instance_name is case-insensitive in SPICE usually, but we'll try exact match first then loose.
        
        lines = subckt_content.splitlines()
        
        # Pattern: Start of line, optional whitespace, instance name, word boundary
        # Then capture the rest of the line
        # Case insensitive search
        pattern = re.compile(r'^\s*' + re.escape(instance_name) + r'\b\s+(.+)', re.IGNORECASE)
        
        target_line = None
        for line in lines:
            # Strip comments (Support both SPICE '*' and Spectre '//')
            if '//' in line:
                code_part = line.split('//')[0].strip()
            else:
                code_part = line.split('*')[0].strip()
            
            # Handle line continuations (+) if we were doing a full parser,
            # but for now assume instance def is on one logical line (simplified).
            # TODO: Improve for multi-line instances if needed.
            
            if pattern.match(code_part):
                target_line = code_part
                break
        
        if not target_line:
            return None
            
        # Now parse the line components
        # Spectre format: Name ( nodes ) ModelName params
        # SPICE format: Name nodes ModelName params
        
        # Normalize parentheses: Replace ( and ) with spaces to treat them as delimiters
        cleaned_line = target_line.replace('(', ' ').replace(')', ' ')
        parts = cleaned_line.split()
        
        # The logic to identify the model name depends on the device type.
        # For 'X' (subcircuit call), the model name is usually the last required argument before params.
        # However, without a schema, it's hard to know which token is the model name vs a node.
        # Heuristic: The model name is often the last token that doesn't look like a parameter (key=value).
        
        # Filter out params (containing '=')
        non_param_parts = [p for p in parts if '=' not in p]
        
        # For X instances: Name node1 ... nodeN ModelName
        # So the last non-param part is likely the model name.
        if instance_name.lower().startswith('x') or instance_name.lower().startswith('i'): # I is common for subckt instance in Spectre
            if len(non_param_parts) >= 2:
                return non_param_parts[-1]
        
        # For Mosfets (M), Resistors (R), etc., the "Model" is also usually near the end or specific position.
        # Let's stick to the "Last non-param token" heuristic for now as a good default for standard SPICE.
        if len(non_param_parts) >= 2:
            return non_param_parts[-1]

        return None

