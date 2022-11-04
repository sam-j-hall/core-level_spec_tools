import numpy as np

######BROADENING PARAMETERS################################

X_START = 275. #Start Value
X_STOP = 330. #End Value
BROAD_1 = 0.75 #Broadening value for first section
BROAD_2 = 2.0 #Broadening value for last section
FIRST_PEAK = 290.0 
EWID_1 = FIRST_PEAK+5.0 #Set range to linearly move from braod1 to BROAD_2
EWID_2 = FIRST_PEAK+15.0
MIX_1 = 0.2 #First G/L mix ratio
MIX_2 = 0.8 #Last G/L mix ratio

######SYSTEM PARAMTERS######################################

MOLECULE = 'azulene' #Name of MOLECULE
METAL = 'Ag' #Surface in system
ELEMENT = 'C'
NUM_START = 48 #First index number of the ATOM directories
NUM_END = 57 #Last index number of the ATOM directories
N_TYPE = 4 #1 for Total NEXAFS, 2 for angular, 3 for polarised, 4 for average polarised
ANGLE = ['t25','t53','t90'] #Incidence ANGLEs
ATOM = '4' #The number of the excited ATOM in the list of ELEMENTs in the system
MO_START = 17 #First MO state to project out
MO_END = 28 #Last MO state to project

######SETUP ALL LIST AND VARIABLES#############################

#Create list of all the ATOMs and MO states
NUMBERS = list(range(NUM_START,NUM_END+1))
MO = list(map(str, range(MO_START,MO_END+1)))

#Create list of all the FOLDERS all the data is in C48/, C49/... C57/
FOLDERS = []
for n in NUMBERS:
    FOLDERS.append(ELEMENT+str(n)+'/')

#Create variable with a string og the delta file which will be read
FILE_NAME = '/' + MOLECULE + '_' + METAL + '_' + ATOM + '_1_1_1_deltas.dat'

#Get the number of kpoints used in calculation in order to correct the MO projected state
K_PTS = []
with open(ELEMENT + str(NUMBERS[0]) + '/' + MOLECULE + '_' + METAL + '.bands', 'r') as BAND_FILE:
    for line in BAND_FILE:
        if 'Number of k-points' in line:
            for word in line.split():
                try:
                    K_PTS.append(float(word))
                except ValueError:
                    pass

#Get the length of the deltas file
BANDS = np.loadtxt(ELEMENT + str(NUMBERS[0]) + '/' + ANGLE[0] + '/' + FILE_NAME)
BANDS_NUM = len(BANDS)

#Read .param file to see if calculation is spin_polarised and set up required settings
with open (ELEMENT + str(NUMBERS[0]) + '/' + MOLECULE + '_' + METAL + '.param') as PARAM_FILE:
    if 'SPIN_POLARIZED: TRUE' in PARAM_FILE.read():
        SPIN = True
        SPIN_VAL = list(map(str,range(1,3)))
        SPIN_NUM = BANDS_NUM/2
    else:
        SPIN = False
        SPIN_VAL = list(map(str, range(1,2)))
        SPIN_NUM = BANDS_NUM

#Create arrays with sized of the system to use
PEAKS = np.zeros([len(NUMBERS), int(SPIN_NUM)])
I = np.zeros([len(NUMBERS), int(SPIN_NUM)])

###############################################
def main():
#Loop over spin, MOs and ANGLEs in the indivdual directories
    for s in SPIN_VAL:
        for m in MO:
            for a in ANGLE:
                for i,direc in enumerate(FOLDERS):
#Load the data from the MolPDOS calculation
                    NEX_DATA = np.loadtxt(direc + a + FILE_NAME)
                    X, Y = NEX_DATA[:,0], NEX_DATA[:,N_TYPE]
#If spin polarized is on then split the data in half for each spin, X_1, Y_1 and X_2, Y_2
                    if SPIN == True:
                        X_1, Y_1 = X[:int(SPIN_NUM)], Y[:int(SPIN_NUM)]
                        X_2, Y_2 = X[int(SPIN_NUM):], Y[int(SPIN_NUM):]
                        SPIN_DICT = {
                                'spin1x' : X_1,
                                'spin2y' : Y_1,
                                'spin2x' : X_2,
                                'spin2y' : Y_2
                                }
#If not spin polarized load all data as x, y
                    else:
                        SPIN_DICT = {
                                'spin1x' : X,
                                'spin1y' : Y,
                                }
#Load the indivdual MO data from the MolPDOS calculation and add the k-point scaling and add
#multiply the intesity of the MO with the overall spectrum
                    NEX_DATA_2 = np.loadtxt(direc + a + '/' + MOLECULE + '_' + METAL + '_' + m + '_spin' + s + '_deltas.dat')
                    NEX_DATA_2 *= K_PTS
                    PEAKS[i,:] = SPIN_DICT['spin' + s + 'x']
                    I[i,:] = SPIN_DICT['spin' + s + 'y'] * NEX_DATA_2[:,1]
#Write out all of the MO data into a delta file
                MO_DEL_FILE = open(MOLECULE + '_' + METAL + '_MO' + m + '_deltas_' + a + '_spin' + s + '.txt','w')
                MO_DEL_FILE.write('#   <x in eV>     Intensity\n')
                for p,i in zip(PEAKS.flatten(), I.flatten()):
                    MO_DEL_FILE.write('{0:16.8f}    {1:16.8f}\n'.format(p,i))
                MO_DEL_FILE.close()
#Apply the BROADENING
                X, Y = dos_binning(PEAKS.flatten(), BROADENING = BROAD_1, MIX_1 = MIX_1, MIX_2 = MIX_2, START = X_START, STOP = X_STOP,
                        COEFFS = I.flatten(), BROADENING_2 = BROAD_2, EWID_1 = EWID_1, EWID_2 = EWID_2)
#Write out MO peak into a text file
                MO_FILE = open(MOLECULE + '_' + METAL + '_MO' + m + '_' + a + '_spin' + s + '.txt', 'w')
                for (X_I, Y_I) in zip(X,Y):
                    MO_DATA = str(X_I) + ' ' + str(Y_I) + '\n'
                    MO_FILE.write(MO_DATA)
                MO_FILE.close()

##############################################################
def gaussian(X, X_MEAN, BROADENING):

    GAUSSIAN_VAL = np.sqrt((4*np.log(2))/(np.pi*(BROADENING**2)))* np.exp(-((4*np.log(2))/(BROADENING**2))*(X-X_MEAN)**2);
    return GAUSSIAN_VAL

def lorentzian(X, X_MEAN, BROADENING):

    LORENTZIAN_VAL = (1/(2*np.pi))* (BROADENING)/(((BROADENING/2)**2)+(X-X_MEAN)**2);
    return LORENTZIAN_VAL

def PseudoVoigt(X, X_MEAN, BROADENING, MIXING):
    """ 
    Combines gaussian and lorentzian schemes together
    """
    return (1-MIXING)*gaussian(X, X_MEAN, BROADENING)+MIXING*lorentzian(X, X_MEAN, BROADENING)

def dos_binning(EIGENVALUES,BROADENING=0.75, BIN_WIDTH=0.01, MIX_1=0., MIX_2 = None,
        COEFFS=None,START=0.0, STOP=10.0, BROADENING_2 = None, EWID_1 = 10.0, EWID_2 = 20.0):
    """ 
    performs binning for a given set of eigenvalues and 
    optionally weight COEFFS.
    """
    if BROADENING_2 is None:
        BROADENING_2 = BROADENING
    if COEFFS is None:
        COEFFS = np.ones(len(EIGENVALUES))

    LOWEST_E = START
    HIGHEST_E = STOP
    NUM_BINS = int((HIGHEST_E-LOWEST_E)/BIN_WIDTH)
    X_AXIS = np.zeros([NUM_BINS])
    DATA = np.zeros([NUM_BINS])
    #setting up x-axis
    for i in range(NUM_BINS):
        X_AXIS[i] = LOWEST_E + i * BIN_WIDTH
    #get DOS
    SIGMA = np.zeros((len(EIGENVALUES)))
    MIXING = np.zeros((len(EIGENVALUES)))

    for ei,e in enumerate(EIGENVALUES):
        if e<=(EWID_1):
            SIGMA[ei]=BROADENING
            MIXING[ei]=MIX_1
        elif e>(EWID_2):
            SIGMA[ei]=BROADENING_2
            MIXING[ei]=MIX_2
        else:
            SIGMA[ei]=BROADENING + ((BROADENING_2-BROADENING)/(EWID_2-EWID_1))*(e-EWID_1)
            MIXING[ei]=(MIX_1 + ((MIX_2-MIX_1)/(EWID_2-EWID_1))*(e-EWID_1))

    for i in range(NUM_BINS):
        PSEUDO_VOIGT_VEC = np.zeros((len(EIGENVALUES)))
        PSEUDO_VOIGT_VEC=PseudoVoigt(X_AXIS[i],EIGENVALUES,SIGMA,MIXING)*COEFFS
        DATA[i]= np.sum(PSEUDO_VOIGT_VEC)
    return X_AXIS, DATA

main()
