import os
import argparse
import copy
import pandas as pd


def process_command():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-path",
        "--path",
        type=str,
        required=True,
        help="path about testbench(.state) and netlist(.scs)",
    )
    return parser.parse_args()


# Transform testbench .xml(active.state + maestro.sdb) into dataframe format
# same as virtuoso view for rule check
def testbench_parser(path):
    # read test_bench file
    try:
        with open(f"{path}/active.state", "r") as file:
            state_content = file.readlines()
    except FileNotFoundError:
        print("File not found")
        return

    testbench_list = []
    is_struct = False
    temp_row = {}

    for line in state_content:
        line = line.strip()

        if is_struct:
            # end of one struct block
            if line.replace(" ", "")[:-1] == "</field>":
                is_struct = False
                testbench_list.append(temp_row)
            continue

        if line.find('<field Name="index" Type="fixnum">') != -1:
            # start a new row
            temp_row = {
                "index": "",
                "Name": "",
                "Type": "",
                "Details": "",
                "Plot": "",
                "Plot Target": "",
                "Save": "",
                "Spec": "",
            }
            idx = line.split('<field Name="index" Type="fixnum">')[1].split("</field>")[0]
            temp_row["index"] = int(idx)

        elif line.find('<field Name="name" Type="string">') != -1:
            name = line.split('<field Name="name" Type="string">')[1].split("</field>")[0]
            temp_row["Name"] = name

        elif line.find('<field Name="signal" Type="string">') != -1:
            details = line.split('<field Name="signal" Type="string">')[1].split("</field>")[0]
            temp_row["Type"] = "signal"
            temp_row["Details"] = details

        elif line.find('<field Name="expression" Type="list">') != -1:
            details = line.split('<field Name="expression" Type="list">')[1].split("</field>")[0]
            temp_row["Type"] = "expr"
            temp_row["Details"] = details

        elif line.find('<field Name="plot" Type="symbol">t</field>') != -1:
            temp_row["Plot"] = True

        elif line.find('<field Name="save" Type="symbol">t</field>') != -1:
            temp_row["Save"] = True

        elif line.find('Type="destruct"') != -1:
            # start struct block which will be filled by following lines
            is_struct = True

    # build dataframe from testbench list
    testbench_df = pd.DataFrame(testbench_list)
    testbench_df = testbench_df.drop_duplicates()
    testbench_df = testbench_df.sort_values(by=["Plot", "index"])

    # read maestro.sdb for spec
    try:
        with open(f"{path}/maestro.sdb", "r") as file:
            sdb_content = file.readlines()
    except FileNotFoundError:
        print("File not found")
        print(testbench_df)
        return testbench_df

    is_spec = False
    resname = ""
    spec = ["", ""]

    for line in sdb_content:
        line = line.strip()

        if is_spec:
            line = line.replace('"', "")
            if line.find("<resname>") != -1:
                resname = line.split("<resname>")[1].split("</resname>")[0]
            elif line.find("<max>") != -1:
                spec_value = line.split("<max>")[1].split("</max>")[0]
                spec = ["max", spec_value]
            elif line.find("<min>") != -1:
                spec_value = line.split("<min>")[1].split("</min>")[0]
                spec = ["min", spec_value]

        if line.find("</spec>") != -1 and is_spec:
            # write spec back to dataframe
            spec_str = f"{spec[0]}: {spec[1]}"
            testbench_df.loc[testbench_df["Name"] == resname, "Spec"] = spec_str
            is_spec = False

        if line.find("<spec>") != -1:
            is_spec = True

    print(testbench_df)
    return testbench_df


# Transform netlist(input.scs) into dictionary/dataframe format for future use
def netlist_parser(path):
    # read netlist file
    try:
        with open(f"{path}/input.scs", "r") as file:
            content = file.readlines()
    except FileNotFoundError:
        print("File not found")
        return

    # merge split line string with "\" to one line string for each cell
    content_merge = []
    merge_line = ""

    for line in content:
        line = line.rstrip("\n")

        if line.endswith("\\"):
            merge_line += line[:-1].strip() + " "
        else:
            merge_line += line
            content_merge.append(merge_line)
            merge_line = ""

    # transfer netlist to dataframe format, each row is an instance
    netlist_df = pd.DataFrame(
        columns=[
            "lib_name",
            "top_cell_name",
            "cell_name",
            "instance_name",
            "type",
            "pin",
            "net",
            "parameter",
        ]
    )

    tmp = pd.DataFrame(columns=netlist_df.columns)

    for line in content_merge:
        line = line.strip()

        # cell name line
        if line.find("cell name") != -1:
            cell_name = line.split(" ")[1]
            tmp.loc[:, "top_cell_name"] = cell_name

        # instance line: inst_name (nets) cell_name params
        elif line.find("(") != -1 and line.find(")") != -1:
            split_line = [
                line.split("(")[0].strip(),
                line.split("(")[1].split(")")[0].strip(),
                line.split(")")[1].strip(),
            ]

            tmp_line = pd.DataFrame(columns=netlist_df.columns)

            tmp_line.loc[0, "instance_name"] = split_line[0].replace("\\", "")
            tmp_line.loc[0, "net"] = split_line[1].split()
            tmp_line.loc[0, "cell_name"] = split_line[2].split(" ")[0].replace("\\", "")

            parameter = {}
            if len(split_line[2].split(" ")) > 1:
                for p in split_line[2].split(" ")[1:]:
                    if p.find("=") != -1:
                        parameter_name = p.split("=")[0]
                        parameter[parameter_name] = p.split("=")[1]
                    else:
                        # parameter without explicit key
                        parameter_name = "p_" + p
                        parameter[parameter_name] = p

            tmp_line.loc[0, "parameter"] = [parameter]
            tmp = pd.concat([tmp, tmp_line], ignore_index=True)

        elif line.find("subckt") != -1:
            if tmp.shape[0] != 0:
                tmp["type"] = "subckt"
                netlist_df = pd.concat([netlist_df, tmp], ignore_index=True)
                tmp = pd.DataFrame(columns=netlist_df.columns)

            library_name = line.split(" ")[1]
            tmp.loc[:, "lib_name"] = library_name
            tmp.loc[:, "type"] = "top"

    if tmp.shape[0] != 0:
        if not pd.isna(tmp.loc[0, "type"]) and not pd.isna(tmp.loc[0, "cell_name"]):
            netlist_df = pd.concat([netlist_df, tmp], ignore_index=True)

    netlist_df = netlist_df.drop_duplicates(
        subset=["lib_name", "top_cell_name", "cell_name", "instance_name"]
    )
    netlist_df.to_csv("netlist_df.csv")

    # ----- hierarchy building helpers -----

    # for netlist hierarchy summary use
    def find_chains(df, current_cell_name, cell_chain, instance_chain, net_list):
        sub_rows = netlist_df[
            (netlist_df["type"] == "subckt")
            & (netlist_df["top_cell_name"] == current_cell_name)
        ]
        if sub_rows.empty:
            return [[cell_chain, instance_chain, net_list]]

        all_chains = []
        for _, sub_row in sub_rows.iterrows():
            next_cell = sub_row["cell_name"]
            next_instance = sub_row["instance_name"]
            next_net = sub_row["net"]
            all_chains.extend(
                find_chains(
                    df,
                    next_cell,
                    cell_chain + [next_cell],
                    instance_chain + [next_instance],
                    net_list + [next_net],
                )
            )
        return all_chains

    # build hierarchy information
    hierarchy_df = pd.DataFrame()
    result_chain = []

    for _, row in netlist_df[netlist_df["type"] == "top"].iterrows():
        current_instance_name = row["instance_name"]
        current_cell_name = row["cell_name"]
        current_net = row["net"]
        chains = find_chains(
            netlist_df,
            current_cell_name,
            [current_cell_name],
            [current_instance_name],
            [current_net],
        )
        result_chain.extend(chains)

    netlist_hierarchy = []
    net_hierarchy = []

    # flatten chains to hierarchy list
    for cell_chain, instance_chain, net_chain in result_chain:
        row = {}
        for i, (cell, instance, net) in enumerate(
            zip(cell_chain, instance_chain, net_chain)
        ):
            row[f"H{i+1}"] = cell
            row[f"H{i+1}_inst"] = instance
            row[f"H{i+1}_net"] = net
        netlist_hierarchy.append(row)

    netlist_hierarchy_path = []
    for instance_chain, net_chain in [(c[1], c[2]) for c in result_chain]:
        row = {}
        for i in range(len(instance_chain)):
            row[f"H{i+1}"] = "/".join(instance_chain[: i + 1])
        netlist_hierarchy_path.append(row)

    netlist_hierarchy_df = pd.DataFrame(netlist_hierarchy)
    netlist_hierarchy_df.to_csv("netlist_hierarchy.csv", index=False)

    netlist_hierarchy_path_df = pd.DataFrame(netlist_hierarchy_path)
    netlist_hierarchy_path_df.to_csv("netlist_hierarchy_path.csv", index=False)


if __name__ == "__main__":
    args = process_command()

    # origin data path is in /nobackup/a_dav2adm_t1/dataHub/for_AIDE with 3 .zip files
    # ANA_D2DPHY_MLINK_1M64B_32G_COWOSS_BS_61959, ANA_D2DPHY_MLINK_1M64B_32G_COWOSS_BS_61953, ANA_D2DPHY_MLINK_1M64B_32G_COWOSS_BS_61953_ver2
    # Please download the .zip file and unzip to the path you want
    #
    # you could use virtuoso to check data with below env setting
    #   module load Virtuoso/23.1.ISR12
    #   module load MMSIM/23.1.SR9
    #   setenv LSB_DEFAULTPROJECT Develop
    #   cd ANA_D2DPHY_MLINK_1M64B_32G_COWOSS_BS_61953
    #   just execute "virtuoso"
    #   select library = MLINK_SB_NB_SIM_MARS, Cell = SIMTR_SB_TX, View will have 2 item maestro(=testbench table) and schematic to check
    #
    # testbench file in "./ANA_D2DPHY_MLINK_1M64B_32G_COWOSS_BS_61959/ANA_D2DPHY_MLINK_1M64B_32G_COWOSS_BS_61959_SIMTR_SB_TX/MLINK_SB_NB_SIM_MARS/SIMTR_SB_TX/maestro"
    # netlist file in "./ANA_D2DPHY_MLINK_1M64B_32G_COWOSS_BS_61959/simulation/MLINK_SB_NB_SIM_MARS/SIMTR_SB_TX/maestro/results/maestro/AutoRun/1/SIMTR_SB_TX/netlist"

    # run different parser
    if args.path.find("simulation") != -1:
        print("run netlist parser")
        netlist_parser(args.path)
    else:
        print("run test_bench parser")
        testbench_parser(args.path)