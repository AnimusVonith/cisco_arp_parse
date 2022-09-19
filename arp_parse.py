import argparse
import re
import pandas as pd
from itertools import combinations
from typing import Optional


def get_in_shape(df: pd.DataFrame, df1: pd.DataFrame) -> pd.DataFrame:
	'''general shaping, prepare dataframes for comparing'''
	return (df[
		(df["Hardware Addr"].isin(df1["Hardware Addr"].to_list()))]
		)[["Address", "Hardware Addr", "Interface"]].reset_index(drop=True).sort_values("Address")


def get_connections(df: pd.DataFrame, df1: pd.DataFrame) -> bool:
	'''compare entries from 2 routers (check if they are connected from show arp command output)'''

	df_dict = {}

	df_dynamic = df[df["State"]=="Dynamic"]
	df1_dynamic = df1[df1["State"]=="Dynamic"]
	
	df_interface = df[df["State"]=="Interface"]
	df1_interface = df1[df1["State"]=="Interface"]

	df_if = get_in_shape(df_interface, df1_dynamic)
	df_dyn = get_in_shape(df_dynamic, df1_interface)
	df1_if = get_in_shape(df1_interface, df_dynamic)
	df1_dyn = get_in_shape(df1_dynamic, df_interface)

	return df_if.equals(df1_dyn) & df1_if.equals(df_dyn)


def get_arp(text: str) -> list:
	'''get show arp output from log'''

	arp_table = text.split("show arp",1)[1]
	arp_table = arp_table.split("******",1)[0]
	arp_table = re.split("-{5}-+(?!-{5}-+)", arp_table)[-1]
	arp_table = arp_table.split("\n")

	return arp_table


def parse_files(files_to_parse: Optional[list[str]] = None) -> list:
	'''return connections between specified routers, if none are supplied start test'''

	if files_to_parse is None:
		files_to_parse = ["172.29.11.20_22", "172.29.11.21_22", "172.29.11.22_22"]

	direct_connections = {}

	for file in files_to_parse:

		ip = file.split("_")[0]

		try:	
			with open(file, "r") as f:
				arp_table = get_arp(f.read())

			new_df = []

			for line in arp_table:
				if line != "":
					new_df.append(re.split("[ ][ ]+", line))

			direct_connections[ip] = pd.DataFrame(new_df[1:], columns=new_df[0])[["Address","Hardware Addr","State","Interface"]]
		except FileNotFoundError:
			print(f"file \"{file}\" not found")
			continue
		except ValueError:
			print(f"file \"{file}\" was not properly formated (standard cisco show arp output)")
		except Exception as e:
			raise e

	list_of_pairs = []

	for pair in combinations(list(direct_connections.keys()),2):
		if get_connections(direct_connections[pair[0]], direct_connections[pair[1]]):
			list_of_pairs.append(f"{pair[0]} <-> {pair[1]}")

	return list_of_pairs


def main():
	'''parse arguments and print returns from parse files function'''
	parser = argparse.ArgumentParser(description='Show connections between routers from Cisco show arp command.\n')
	parser.add_argument('input_files', metavar='input_file', type=str, nargs='*',
	                    help='names of input files with cisco show arp command')

	args = parser.parse_args()

	input_files = args.input_files if args.input_files else None

	print("\n".join(parse_files(input_files)))


if __name__ == '__main__':
	main()