import os
import sys

def print_T1s(T1s):
  if T1s != set():
    for item in sorted(T1s):
        print(" -" + str(item))

def print_T2s(T2s):
  if T2s != set():
    T1s = {}
    for item in T2s:
      if item[0] not in T1s:
        T1s[item[0]] = [item[1]]
      else:
        T1s[item[0]].append(item[1])
    for item in sorted(T1s):
        print(" -" + str(item) + ":")
        for T2 in sorted(T1s[item]):
          print("   -" + str(T2))

def print_T3s(T3s):
  if T3s != set():
    T1s = {}
    for item in T3s:
      if item[0] not in T1s:
        T1s[item[0]] = [(item[1], item[2])]
      else:
        T1s[item[0]].append((item[1], item[2]))

    for T1 in sorted(T1s):
      print(" -" + str(T1) + ":")
      T2s = {}
      for item in T1s[T1]:
        if item[0] not in T2s:
          T2s[item[0]] = [item[1]]
        else:
          T2s[item[0]].append(item[1])

      for item in sorted(T2s):
        print("   -" + str(item) + ":")
        for T3 in sorted(T2s[item]):
          print("     -" + str(T3))

def compare_two_groups(A, B, name_A, name_B):
  shared_T1s = set()
  shared_T2s = set()
  shared_T3s = set()

  A_T1s = set()
  A_T2s = set()
  A_T3s = set()
  for item in A:
    A_T1s.add(item[1])
    A_T2s.add((item[1], item[2]))
    A_T3s.add((item[1], item[2], item[3]))

  B_T1s = set()
  B_T2s = set()
  B_T3s = set()
  for item in B:
    B_T1s.add(item[1])
    B_T2s.add((item[1], item[2]))
    B_T3s.add((item[1], item[2], item[3]))

  unique_A_T1s = set()
  for item in A_T1s:
    if item not in B_T1s:
      unique_A_T1s.add(item)
    else:
      shared_T1s.add(item)
  
  unique_A_T2s = set()
  for item in A_T2s:
    if item not in B_T2s:
      unique_A_T2s.add(item)
    else:
      shared_T2s.add(item)
  
  unique_A_T3s = set()
  for item in A_T3s:
    if item not in B_T3s:
      unique_A_T3s.add(item)
    else:
      shared_T3s.add(item)

  sub_unique_A_T2s = set()
  for item in A:
    if (item[1], item[2]) in unique_A_T2s and item[1] not in unique_A_T1s:
      sub_unique_A_T2s.add((item[1], item[2]))

  sub_unique_A_T3s = set()
  for item in A:
    if (item[1], item[2], item[3]) in unique_A_T3s and item[1] not in unique_A_T1s and (item[1], item[2]) not in unique_A_T2s:
      sub_unique_A_T3s.add((item[1], item[2], item[3]))

  unique_B_T1s = set()
  for item in B_T1s:
    if item not in A_T1s:
      unique_B_T1s.add(item)
  
  unique_B_T2s = set()
  for item in B_T2s:
    if item not in A_T2s:
      unique_B_T2s.add(item)
  
  unique_B_T3s = set()
  for item in B_T3s:
    if item not in A_T3s:
      unique_B_T3s.add(item)

  sub_unique_B_T2s = set()
  for item in B:
    if (item[1], item[2]) in unique_B_T2s and item[1] not in unique_B_T1s:
      sub_unique_B_T2s.add((item[1], item[2]))

  sub_unique_B_T3s = set()
  for item in B:
    if (item[1], item[2], item[3]) in unique_B_T3s and item[1] not in unique_B_T1s and (item[1], item[2]) not in unique_B_T2s:
      sub_unique_B_T3s.add((item[1], item[2], item[3]))

  print("Group A:", name_A)
  print("Group B:", name_B)
  print()

  print("Tier 1 differences:")
  if unique_A_T1s != set():
    print("A has unique T1 fields:")
    print_T1s(unique_A_T1s)
  if unique_B_T1s != set():
    print("B has unique T1 fields:")
    print_T1s(unique_B_T1s)
  print()

  print("Tier 2 differences:")
  if sub_unique_A_T2s != set():
    print("A has unique T2 fields:")
    print_T2s(sub_unique_A_T2s)
  if sub_unique_B_T2s != set():
    print("B has unique T2 fields:")
    print_T2s(sub_unique_B_T2s)
  print()

  print("Tier 3 differences:")
  if sub_unique_A_T3s != set():
    print("A has unique T3 fields:")
    print_T3s(sub_unique_A_T3s)
  if sub_unique_B_T3s != set():
    print("B has unique T3 fields:")
    print_T3s(sub_unique_B_T3s)
  print()

  print("Shared Tier 1 fields:")
  print_T1s(shared_T1s)
  print()

  print("Shared Tier 2 fields:")
  print_T2s(shared_T2s)
  print()

  print("Shared Tier 3 fields:")
  print_T3s(shared_T3s)
      
def process_groups(groups, title, global_params):
  if "output_dir" in global_params.keys() and len(groups) > 1:
    path = "%s/%s" % (global_params["output_dir"], title.strip().replace(" ", "_"))
    if not os.path.exists(path): os.mkdir(path)
    for groupA in groups:
        home_name = ""
        for name in groups[groupA]:
            home_name += name + "_"
        path = "%s/%s/%s" % (global_params["output_dir"], title.strip().replace(" ", "_"), home_name[:-1])
        if not os.path.exists(path): os.mkdir(path)
        for groupB in groups:
            if groups[groupA] != groups[groupB]:
                away_name = ""
                for name in groups[groupB]:
                    away_name += name + "_"

                orig_stdout = sys.stdout
                
                with open("%s/%s/%s/%svs_%spostproccess" % (global_params["output_dir"], title.strip().replace(" ", "_"), home_name[:-1], home_name, away_name), "w") as f:
                    sys.stdout = f
                    compare_two_groups(eval(groupA), eval(groupB), home_name[:-1], away_name[:-1])
                    sys.stdout = orig_stdout