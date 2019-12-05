import ClientSide2 #custom package

import numpy as np
import argparse
import json
import os
import ClassifierFunctions2 as cf

from matplotlib import pyplot as plt
from builtins import input

from Notation import SpaceGroupsDict as spgs
SpGr = spgs.spacegroups()



from itertools import combinations,chain


# Initialize essential global variables
#URL =  "" #you'll need me to send you the link
FAMILIES = ["triclinic","monoclinic","orthorhombic","tetragonal",
        "trigonal","hexagonal","cubic"]

DEFAULT_SESSION = os.path.join ("Sessions","session.json")
DEFAULT_USER = "user_profile.json"
SERVER_INFO = "server_gen2.json"

# list of three, one per level
prediction_per_level = [1, 2, 2]


def build_parser():
    parser = argparse.ArgumentParser()

    # This will be implemented as rollout broadens
    parser.add_argument('--apikey', type=str,
                        dest='key', help='api key to securely access service',
                        metavar='KEY', required=False)

    parser.add_argument('--session',
                        dest='session',help='Keep user preferences for multirun sessions',
                        metavar='SESSION',required=False, default=None)
    return parser

def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))



def combination_peaks(peak_batch, chem_vec, mode, temp_name, crystal_family, user_info, URL, prediction_per_level):

    outpath = "Ready"
    find_valid_peaks = list(powerset(peak_batch["vec"]))
    find_valid_peaks = [item for item in find_valid_peaks if len(item) > 2 and len(item) < 6]
    print(len(find_valid_peaks),"valid peak combinations")

    valid_peaks_combinations = [{"vec":proto_combo} for proto_combo in find_valid_peaks]
    found = False
    threshold = 0
    tot_spec = 1
    for p in prediction_per_level:
        tot_spec *= p
    guesses = {}
    for k in range(1,tot_spec+1):
        guesses["species_"+str(k)]=[]
#    print(guesses)
    common_peaks = []
    failed_combos = valid_peaks_combinations
    #peak_locs,user_info,URL,fam
    persistance = 0
    LIMIT = 3
#    print(failed_combos)
    while len(failed_combos) > 0 and persistance < LIMIT:
        for combo in failed_combos:
            try:
#                print('---classifying---')
#                print(combo)
                classificated = ClientSide2.Send_For_Classification(combo, chem_vec, mode, crystal_family, user_info, URL, prediction_per_level)
                print(classificated)
                classificated["file_name"] = temp_name
#                print('name =')
#                print(temp_name)
                print(os.path.join(outpath,temp_name))
                cf.write_to_csv(os.path.join(outpath,temp_name) + ".csv", classificated, prediction_per_level)
                print(tot_spec)
                for k in range(1,tot_spec+1):
#                    print(k)
#                    print(guesses['species_'+str(k)])
#                    print(classificated["species_"+str(k)])
                    guesses['species_'+str(k)].append( classificated["species_"+str(k)] )
                    common_peaks.append(classificated["species_"+str(k)])
                    
#                guesses['species_2'].append(classificated["species_2"])
#                guesses['species_3'].append(classificated["species_3"])
#                guesses['species_4'].append(classificated["species_4"])
            
#                common_peaks.append(classificated["species_2"])
#                common_peaks.append(classificated["species_3"])
#                common_peaks.append(classificated["species_4"])
                
                # remove the classified combination
#                print('guesses=')
#                print(guesses)
#                print('common_peaks=')
#                print(common_peaks)
                failed_combos.remove(combo)
                
            except KeyboardInterrupt:
                raise
            except:
                print("An error occured this combination was not classified.\nIt will be retried {} more times".format(LIMIT-persistance))

        persistance += 1

    if len(failed_combos)>0:
        print("there were {} failed combinations".format(len(failed_combos)))
    print('returning')
    return common_peaks, guesses


def main():

    parser = build_parser()
    options = parser.parse_args()

    #print(options.session)

    # opens the user specified session
    if options.session:
        with open(os.path.join("Sessions",options.session),'r') as f:
            session = json.load(f)

    # opens the default session    
    else:
        with open(DEFAULT_SESSION,'r') as f:
            session = json.load(f)

    # set variables from loaded session data
#    print(session)
    file_path = session["file_path"]
    output_file = session["output_file"]
    manual_peak_selection = session["manual_peak_selection"]
    known_family = session["known_family"]
    chemistry = session["chemistry"]
    diffraction = session["diffraction"]
    
    mode = ""
    
    if diffraction:
        if chemistry:
            mode="DiffChem"
        else:
            mode="DiffOnly"
    else:
        if chemistry:
            raise ValueError('Running chemistry only predictions is currently not implemented')
        else:
            raise ValueError('Invalid prediction type. Either diffraction or chemistry must be enabled')

    if known_family and known_family=='yes':
        print('known family')
        crystal_family = session["crystal_family"]
        prediction_per_level[0] = 1
    else:
        crystal_family = None
    
    # Load user from provided path, [IN PROGRESS]
    if session["user_info"]:
        with open(session["user_info"],'r') as f:
            user_info = json.load(f)
    else:
        with open(DEFAULT_USER,'r') as f:
            user_info = json.load(f)
    
    with open(session["server_info"],'r') as f:
        server_info = json.load(f)
        
    if server_info['URL']:
        url = server_info['URL']
    else:
        raise ValueError('you need to have the server URL provided to you')
    
    chem_vec = cf.check_for_chemistry(session)
        
    print(file_path)
    print('---starting loop--')
    # Determine if the path is a directory or a file
    if os.path.isdir(file_path):
        print("loading files from directory")
        file_paths = []
        for dirpath,dirnames,fpath in os.walk(file_path):
            for path in fpath:
                file_paths.append(os.path.join(dirpath,path))
        print("found {} files to load.".format(len(file_paths)))

    else:
        file_paths = [file_path]
    

    print(file_paths)
    for f_path in file_paths:

        # Load Data from specified file (DM3, TIFF, CSV etc....)
        
        print("loading data from {}".format(f_path))
        image_data,scale = ClientSide2.Load_Profile(f_path)
        print("I successfully loaded the data")
        
#        print(scale)

        if diffraction:
            peak_locs,peaks_h = ClientSide2.Find_Peaks(image_data,scale)
            # Choose which peaks to classify on
            if manual_peak_selection:
                peak_locs = cf.choose_peaks(peak_locs,peaks_h)
                #raise NotImplementedError
        else:
            peak_locs = []
            peaks_h = []
#        
#        print(peak_locs)
#        print(chem_vec)

        
        
        common_peaks,guesses = combination_peaks(peak_locs, chem_vec, mode, f_path.split(os.sep)[-1][:-4], crystal_family, user_info, url, prediction_per_level)
        
        if crystal_family:
            lower_gen = SpGr.edges["genus"][crystal_family][0]
            upper_gen = SpGr.edges["genus"][crystal_family][1]
        else:
            lower_gen = SpGr.edges["genus"][FAMILIES[0]][0]
            upper_gen = SpGr.edges["genus"][FAMILIES[-1]][1]
        fam_range = range(SpGr.edges["species"][lower_gen][0],1+SpGr.edges["species"][upper_gen][1])
            
        #        phi = 2*np.pi/360
        fig_ang = 300
        phi = (2*np.pi*fig_ang/360)/(max(fam_range)-min(fam_range)+1)
        thet = fig_ang/(max(fam_range)-min(fam_range)+1)
        fam_axes = [1,3,16,75,143,168,195]
        fig1 = plt.figure(1,figsize=(len(fam_range),8))
#        ax1 = fig1.add_axes([0.1,0.1,.8,.8])

        plt.ion
        fig2 = plt.figure(2,figsize=(8,8))
        plt.ion
        ax2 = fig2.add_axes([0.1,0.1,0.8,0.8],polar=True)
        ax2.set_thetamax(1)
        ax2.set_thetamax(fig_ang)
        ax2.set_theta_zero_location("S",offset=30)
        #        ax2.set_theta_zero_location("N")
        ax2.set_thetagrids([f*thet for f in fam_axes],labels = FAMILIES)
        prev_histograms = []
        plots_1 = []
        plots_2 = []
        #        print('guesses = ')
        #        print(guesses)
        num_pred = np.prod(prediction_per_level)
        for rank in range(1,num_pred+1):
            histo = np.histogram([int(g) for g in guesses["species_{}".format(rank)]],bins=fam_range)
            if rank > 1:
                plt.figure(1)
                plot_1 = plt.bar(histo[1][:-1], histo[0], bottom = np.sum(np.vstack(prev_histograms), axis=0), align="center", width = 1)
                plt.figure(2)
                plot_2 = plt.bar(histo[1][:-1]*phi, histo[0], bottom = np.sum(np.vstack(prev_histograms), axis=0),align="center", width = 2*phi)
            else:
                plt.figure(1)
                plot_1 = plt.bar(histo[1][:-1], histo[0], align="center", color='red', width = 1)
                plt.figure(2)
                plot_2 = plt.bar(histo[1][:-1]*phi, histo[0], align="center", color='red', width = 2*phi)
            plots_1.append(plot_1)
            plots_2.append(plot_2)
            plt.figure(1)
            plt.yticks(rotation='vertical')
            plt.xticks(histo[1][:-1],rotation='vertical')
            prev_histograms.append(histo[0])
            plt.figure(2)
        #            ax2.set_xticks(histo[1][:-1])

        plt.figure(1)
        plt.xlabel("Prediction",fontsize=10)
        plt.ylabel("Counts",fontsize=10)
        #        plt.legend(plots,("species_1","species_2","species_3","species_4"))
        leg_list = [ "species_{}".format(k+1) for k in range(num_pred) ]
        plt.legend(plots_1,leg_list)
        print("Results/"+f_path.split(os.sep)[-1][:-4]+"_gen2.png")
        plt.savefig("Results/"+f_path.split(os.sep)[-1][:-4]+"_gen2.png")

        plt.figure(2)
        #        plt.xlabel("Prediction",fontsize=10,rotation='vertical')
        #        plt.ylabel("Counts",fontsize=10)
        plt.legend(plots_2,leg_list)
        #        plt.legend(plots,("species_1","species_2","species_3","species_4"))
        print("Results/"+f_path.split(os.sep)[-1][:-4]+"_gen2_polar.png")
        plt.savefig("Results/"+f_path.split(os.sep)[-1][:-4]+"_gen2_polar.png")
        #        plt.show(block=False)
        

if __name__ == "__main__":
    main()


