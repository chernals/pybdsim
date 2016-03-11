import pymadx.Ptc
import pymadx.Beam
import pymadx.Builder
import pymadx.Tfs
import pybdsim.Beam
import pybdsim.Builder
import pybdsim.Data
import pybdsim.Convert
import pybdsim.Testing
import pybdsim.Plot
import pymadx as _pymadx
import os as _os
import matplotlib.pyplot as _plt
import robdsim
import numpy as _np
import root_numpy as _rnp
import matplotlib.backends.backend_pdf
import matplotlib.patches as mpatches
import time

from scipy.stats import binned_statistic


class LatticeTest:
    def __init__(self,filepath, nparticles = 1000, verbose=False):        
        """
        Takes a .madx file containing description of a lattice and generates
        BDSIM and MadX PTC jobs from it as well as MadX optical functions 
        propagation plots.

        nparticles: specifies the number of particles to be used for BDSIM/PTC runs. Default = 1000
        verbose   : prints additional information
        """
        cwd        = _os.getcwd()
        path       = filepath.split("/")
        filename   = path[-1]                         #last element is the filename
        
        if(path[0]=="/"):                             #when absolute filepath is given
            folderpath = path[:-1]
        elif(path[0]=="." and path[1]=="/"):          #when ./ is used to specify current folder
            path=path[1:]
            folderpath = cwd+"/".join(path[:-1])      #when relative filepath is given
        else:
            folderpath = cwd+"/"+"/".join(path[:-1])  #when relative filepath is given

        print "Filename: ",filename
        print "Folderpath: ",folderpath
        
        if filename[-5:] == ".madx":                
            self.filename    = filename[:-5]
            self.tfsfilename = str.lower(self.filename)
            self.filepath    = filepath
            self.folderpath  = folderpath
            self.ptcinrays   = self.filename+"_inrays.madx"
            self.ptcfilename = "ptc_"+self.filename+".madx"
            self.nparticles  = nparticles
            self.verbose     = verbose
            self.flipmagnets = False
            self.figureNr    = 1729
        else:
            raise IOError('Invalid file format, MadX file (.madx) required')

    def CleanRunCompare(self):
        self.Clean()
        self.Run()
        self.Compare(addPrimaries=False)

    def Clean(self):
        """
        Delete all files produced during the testing, including
        .log .dat .tfs. .ps ptc* .txt .root .gmad inrays .png .pdf
        """
        _os.chdir(self.folderpath)
        
        _os.system("rm -rf *.log")
        _os.system("rm -rf *.dat")
        _os.system("rm -rf *.tfs")
        _os.system("rm -rf *.ps")
        _os.system("rm -rf ptc*")
        _os.system("rm -rf *.txt")
        _os.system("rm -rf *.root")
        _os.system("rm -rf *.gmad")
        _os.system("rm -rf *_inrays.madx")
        _os.system("rm -rf *.png")
        _os.system("rm -rf *.pdf")
        _os.system("rm trackone")

        # clean and close figures (10 figures in total)
        for i in range(11):
            _plt.close(self.figureNr+i)

    def CleanOutput(self):
        """
        Delete output files files produced during the testing, while
        preserving lattice definitions. Useful for beam parameter testing.
        Deleted files include .dat .txt .root inrays .png .pdf
        """
        _os.chdir(self.folderpath)      
        _os.system("rm -rf *.dat")
        _os.system("rm -rf *.root")
        _os.system("rm -rf *.txt")
        _os.system("rm -rf *.png")
        _os.system("rm -rf *.pdf")
        _os.system("rm trackone")

        # clean and close figures (10 figures in total)
        for i in range(11):
            _plt.close(self.figureNr+i)

    def RunParams(self, bdsim='bdsim', madx='madx'):
        """
        Allows a bdsim and ptc run with already defined lattices. Used for tests of element thinning.
        """
        print 'Test> Running new parameters: ', self.filename

        _os.chdir(self.folderpath)
        _os.system(bdsim+" --file="+self.filename+".gmad --ngenerate="+str(self.nparticles)+" --batch --output=root --outfile="+self.filename+" > bdsim.log")
        pybdsim.Testing.BdsimPrimaries2Ptc(''+self.filename+'.root', self.ptcinrays)
        _os.system(madx+" < "+self.ptcfilename+" > ptc_madx.log")


    def Run(self, bdsim='bdsim', madx='madx'):
        print 'Test> Lattice: ', self.filename 
        print 'Test> Destination filepath: ', self.filepath

        _os.chdir(self.folderpath)

        _os.system(madx + " < "+self.filename+".madx > madx.log")

        """
        a = pybdsim.Convert.MadxTfs2Gmad(''+self.tfsfilename+'.tfs','dump',beam=False)
        b = pybdsim.Beam.Beam('proton',10.0,'ptc')    #beam parameters need to be set manually
        b.SetDistribFileName('INRAYS.madx')           #This is for testing BDSIM 'ptc' beam distribution
        a.AddBeam(b)
        a.Write(self.filename)
        
        """
        #Load Tfs file to check particle type and flip BDSIM magnet polarities as needed
        tfs  = _pymadx.Tfs(self.tfsfilename+'.tfs')
        particle = tfs.header['PARTICLE']
        if particle == 'ELECTRON' :
            self.flipmagnets = True
        
        pybdsim.Convert.MadxTfs2Gmad(self.tfsfilename+'.tfs', self.filename,flipmagnets=self.flipmagnets ,verbose=self.verbose)                        
        
        _pymadx.MadxTfs2Ptc(''+self.tfsfilename+'.tfs', self.ptcfilename, self.ptcinrays)

        _os.system(bdsim+" --file="+self.filename+".gmad --ngenerate="+str(self.nparticles)+" --batch --output=root --outfile="+self.filename+" > bdsim.log")

        pybdsim.Testing.BdsimPrimaries2Ptc(''+self.filename+'.root', self.ptcinrays)

        _os.system(madx+" < "+self.ptcfilename+" > ptc_madx.log")


    def Compare(self, plot='all', addPrimaries=False, showPlots=False, showResiduals=True):
        """
        Performs analysis and comparison of BDSIM, MADX and MADX-PTC output. 
       
        addPrimaries - True adds BDSIM primaries to histos. Default is False
        plot         - | beta | emittance | alpha |  - specify optical function to plot
        showPlots    - True diplays the plots to screen
        """

        _os.chdir(self.folderpath)

        #Load data
        isValid  = False
        attempts = 0
        
        while(isValid==False and attempts<=5):
            rootdata  = robdsim.RobdsimOutput(self.filename+".root")
            print "robdsim.RobdsimOutput> root file loaded"
        
            primchain = rootdata.GetSamplerChain('Primaries')
            bdsimprim = _rnp.tree2rec(primchain)
            Bx0 = bdsimprim['x']
            By0 = bdsimprim['y']
            Bxp0 = bdsimprim['xp']
            Byp0 = bdsimprim['yp']
            self.bdsimprimaries = {'x':Bx0,'y':By0,'xp':Bxp0,'yp':Byp0}
            
            trees = rootdata.GetVectorOfTreeNames()
            for index,tree in enumerate(trees):
                if tree == 'ElossTree':
                    final_sampler = trees[index-1]
                    break
            print( "End sampler found to be " + final_sampler)
            endchain = rootdata.GetSamplerChain(final_sampler)
            bdsim = _rnp.tree2rec(endchain)
            Bx = bdsim['x']
            By = bdsim['y']
            Bxp = bdsim['xp']
            Byp = bdsim['yp']
            self.bdsimoutput = {'x':Bx,'y':By,'xp':Bxp,'yp':Byp}
            
            madxout = pymadx.Tfs("trackone")
            madxend = madxout.GetSegment(madxout.nsegments) #get the last 'segment' / sampler
            Mx = madxend.GetColumn('X')
            My = madxend.GetColumn('Y') 
            Mxp = madxend.GetColumn('PX')
            Myp = madxend.GetColumn('PY')
            self.ptcoutput = {'x':Mx,'y':My,'xp':Mxp,'yp':Myp}

            #Check all particles make it through
            if(len(Bx)!=len(Mx)):
                    print "Input particles: ",self.nparticles," BDS_out particles: ", len(Bx)," PTC_out particles: ", len(Mx)       
                    print "Warning:  Unequal number of output particles! Attempting again..."
                    attempts += 1
                    print "Attempt: ", attempts
                    self.Clean()
                    self.Run()                  
            else:
                isValid = True

            if(attempts==5):
                print "Run unsuccessful, please check parameters and try again"
                return
                
        if showResiduals:
            # residuals
            fresx  = Mx - Bx
            fresy  = My - By
            fresxp = Mxp - Bxp
            fresyp = Myp - Byp
            self.residuals = {'x':fresx,'y':fresy,'xp':fresxp,'yp':fresyp}
                
            """    
            # fractional residuals
            fresx  = _np.nan_to_num((Mx - Bx)/Mx)
            fresy  = _np.nan_to_num((My - By)/My)
            fresxp = _np.nan_to_num((Mxp - Bxp)/Mxp)
            fresyp = _np.nan_to_num((Myp - Byp)/Myp)
            self.residuals = {'x':fresx,'y':fresy,'xp':fresxp,'yp':fresyp}
            """

            print "Average residuals:"," x(m): ",_np.mean(fresx)," y(m): ",_np.mean(fresy)
            print " xp(rad): ",_np.mean(fresxp)," yp(rad): ",_np.mean(fresyp)
            
            #standard deviation
            stdMx  = _np.std(Mx)
            stdMy  = _np.std(My)
            stdMxp = _np.std(Mxp)
            stdMyp = _np.std(Myp)

            stdBx  = _np.std(Bx)
            stdBy  = _np.std(By)
            stdBxp = _np.std(Bxp)
            stdByp = _np.std(Byp)

            #standard devation fractional errors
            frestdx  = _np.nan_to_num(stdMx - stdBx)
            frestdy  = _np.nan_to_num(stdMy - stdBy)
            frestdx  = _np.nan_to_num(frestdx / stdMx) #protect against nans for 0 diff
            frestdy  = _np.nan_to_num(frestdy / stdMy)
            frestdxp = _np.nan_to_num(stdMxp - stdBxp)
            frestdyp = _np.nan_to_num(stdMyp - stdByp)
            frestdxp = _np.nan_to_num(frestdxp / stdMxp)
            frestdyp = _np.nan_to_num(frestdyp / stdMyp)

            # write standard deviations to file
            with open(''+self.filename+'_stdev.txt', 'w') as stdout:
                timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")
                t = timestamp+' '+self.filename+' Standard Deviations (particles = '+str(self.nparticles)+'): \n'
                h = 'BDSIM_X \t MX-PTC_X \t BDSIM_Y \t MX-PTC_Y \t BDSIM_XP'
                h+= ' \t MX-PTC_XP \t BDSIM_YP \t MX-PTC_YP \t FRCERR_X \t FRCERR_Y \t FRCERR_XP \t FRCERR_YP \n'
                s  = "{0:.4e}".format(stdBx)
                s += '\t' +  "{0:.4e}".format(stdMx)
                s += '\t' +  "{0:.4e}".format(stdBy)              
                s += '\t' +  "{0:.4e}".format(stdMy)
                s += '\t' +  "{0:.4e}".format(stdBxp)
                s += '\t' +  "{0:.4e}".format(stdMxp)
                s += '\t' +  "{0:.4e}".format(stdByp)
                s += '\t' +  "{0:.4e}".format(stdMyp)
                s += '\t' +  "{0:.4e}".format(frestdx)
                s += '\t' +  "{0:.4e}".format(frestdy)
                s += '\t' +  "{0:.4e}".format(frestdxp)
                s += '\t' +  "{0:.4e}".format(frestdyp) + '\n'
                stdout.writelines(t)
                stdout.writelines(h)
                stdout.writelines(s)            
        
        #Loading output and processing optical functions
        madx = pymadx.Tfs(''+self.tfsfilename+'.tfs')

        #Writes the text file for RobdsimAnalysis
        with open(''+self.filename+'_robds_anal.txt', 'w') as outfile:
            outfile.writelines("{:<40s}".format('Debug')+'\t 0\n')
            outfile.writelines("{:<40s}".format('InputFilePath')+'\t ./'+self.filename+'.root \n')
            outfile.writelines("{:<40s}".format('OutputFileName')+'\t ./'+self.filename+'_optics.root \n')
            outfile.writelines("{:<40s}".format('CalculateOpticalFunctions')+'\t 1 \n')
            outfile.writelines("{:<40s}".format('CalculateOpticalFunctionsFileName')+'\t ./'+self.filename+'_optics.dat \n')

        #Calculates optical functions and produces .root and .dat files for analysis 
        _os.system("robdsimAnal "+self.filename+"_robds_anal.txt")
        
        bdata  = pybdsim.Data.Load(''+self.filename+'_optics.dat')

        ptcfile  = 'ptc_'+self.filename+'_opticalfns.dat'
        print "ptcCalculateOpticalFunctions> processing... " , ptcfile 
        ptc      = _pymadx.PtcAnalysis(ptcOutput="trackone") 
        ptc.CalculateOpticalFunctions(ptcfile)
        ptcdata  = pybdsim.Data.Load(ptcfile)

        #Get the S coordinate from all outputs
        M_s       = madx.GetColumn('S')
        B_s       = bdata.S()
        PTC_s     = ptcdata.S()

        M_emittx  = madx.header['EX'] #Get emittance from tfs file header
        M_emitty  = madx.header['EY'] #To be used in emittance and sigma plots

        plotopts = [] #keep track of plots
        plotNr   = 0

        if  (plot == "all"):
            plotopts.append("beta")
            plotopts.append("dispersion_xy")
            #plotopts.append("dispersion_xpyp")
            plotopts.append("alpha")
            plotopts.append("emittance")
            plotopts.append("sigma_xy")
            #plotopts.append("sigma_xpyp")
        else:
            plotopts.append(plot)

        

        #optfn denotes the selected optical function to plot
        in_Tfs = True       #some of the calculated optical functions are not present in the tfs file (e.g emittance,sigmas)
                            #and hence plots and residuals between BDSIM and MADX cannot be obtained
        for opt in plotopts:
            print "bdsimMadx... plotting ", opt
            if (opt=='beta'):
                fn_name      = r'\beta' #this is a raw string for Latex labels and titles
                fn_rname     = 'beta'   #this is reduced name for filename of saved figure
                fn_subsc     = ['_{x}','_{y}']
                fn_units     = '(m)'
                plotNr      += 1
                
                M_optfn_x    = madx.GetColumn('BETX') 
                M_optfn_y    = madx.GetColumn('BETY')
                B_optfn_x    = bdata.Beta_x()
                B_optfn_y    = bdata.Beta_y()
                B_opterr_x   = bdata.Sigma_beta_x()
                B_opterr_y   = bdata.Sigma_beta_y()
                PTC_optfn_x  = ptcdata.Beta_x()
                PTC_optfn_y  = ptcdata.Beta_y()
                PTC_opterr_x = ptcdata.Sigma_beta_x()
                PTC_opterr_y = ptcdata.Sigma_beta_y()
                
                print 'LenMopt ',len(M_optfn_x),' LenMs ',len(M_s),' LenBs ',len(B_s),' LenBopt ',len(B_optfn_x)
                
            elif (opt=='alpha'):
                fn_name      = r'\alpha' #this is a raw string for Latex labels and titles
                fn_rname     = 'alpha'   #this is reduced name for filename of saved figure
                fn_subsc     = ['_{x}','_{y}']
                fn_units     = ''
                plotNr      += 1
                
                M_optfn_x    = madx.GetColumn('ALFX') 
                M_optfn_y    = madx.GetColumn('ALFY')
                B_optfn_x    = bdata.Alph_x()
                B_optfn_y    = bdata.Alph_y()
                B_opterr_x   = bdata.Sigma_alph_x()
                B_opterr_y   = bdata.Sigma_alph_y()
                PTC_optfn_x  = ptcdata.Alph_x()
                PTC_optfn_y  = ptcdata.Alph_y()
                PTC_opterr_x = ptcdata.Sigma_alph_x()
                PTC_opterr_y = ptcdata.Sigma_alph_y()

            elif (opt=='sigma_xy'):
                fn_name      = r'\sigma'  
                fn_rname     = 'sigma_xy' 
                fn_subsc     = ['_{x}','_{y}']
                fn_units     = '(m)'
                plotNr      += 1
                
                in_Tfs       = True
                M_optfn_x    = _np.sqrt(madx.GetColumn('BETX')*M_emittx) 
                M_optfn_y    = _np.sqrt(madx.GetColumn('BETY')*M_emitty)
                B_optfn_x    = bdata.Sigma_x()
                B_optfn_y    = bdata.Sigma_y()
                B_opterr_x   = bdata.Sigma_sigma_x()
                B_opterr_y   = bdata.Sigma_sigma_y()
                PTC_optfn_x  = ptcdata.Sigma_x()
                PTC_optfn_y  = ptcdata.Sigma_y()
                PTC_opterr_x = 0.000001 #not implemented in PTC yet
                PTC_opterr_y = 0.000001
                
            elif (opt=='sigma_xpyp'):
                fn_name      = r'\sigma'
                fn_rname     = 'sigma_xpyp'
                fn_subsc     = ['_{xp}','_{yp}']
                fn_units     = '(rad)'
                plotNr      += 1

               # print "Warning: Sigma not present in MADX tfs file, plotting only MADX-PTC and BDSIM results "
                in_Tfs       = True
                M_optfn_x    = _np.sqrt(M_emittx/madx.GetColumn('BETX')) 
                M_optfn_y    = _np.sqrt(M_emittx/madx.GetColumn('BETY'))
                B_optfn_x    = bdata.Sigma_xp()
                B_optfn_y    = bdata.Sigma_yp()
                B_opterr_x   = bdata.Sigma_sigma_xp()
                B_opterr_y   = bdata.Sigma_sigma_yp()
                PTC_optfn_x  = ptcdata.Sigma_xp()
                PTC_optfn_y  = ptcdata.Sigma_yp()
                PTC_opterr_x = 0.000001 #not implemented in PTC yet
                PTC_opterr_y = 0.000001       

            elif (opt=='emittance'):
                fn_name      = r'\epsilon' #this is a raw string for Latex labels and titles
                fn_rname     = 'emittance'   #this is reduced name for filename of saved figure
                fn_subsc     = ['_{x}','_{y}']
                fn_units     = '(m)'
                plotNr      += 1
                
                #print "Warning: Emittance not present in MADX tfs file, plotting only MADX-PTC and BDSIM results "
                in_Tfs       = True
                M_optfn_x    = _np.empty(len(M_s));
                M_optfn_x.fill(M_emittx)
                M_optfn_y    = _np.empty(len(M_s));
                M_optfn_y.fill(M_emitty)
                B_optfn_x    = bdata.Emitt_x()
                B_optfn_y    = bdata.Emitt_y()
                B_opterr_x   = bdata.Sigma_emitt_x()
                B_opterr_y   = bdata.Sigma_emitt_y()
                PTC_optfn_x  = ptcdata.Emitt_x()
                PTC_optfn_y  = ptcdata.Emitt_y()
                PTC_opterr_x = ptcdata.Sigma_emitt_x()
                PTC_opterr_y = ptcdata.Sigma_emitt_y()

            elif (opt=='dispersion_xy'):
                fn_name      = r'D'              #this is a raw string for Latex labels and titles
                fn_rname     = 'dispersion_xy'   #this is reduced name for filename of saved figure
                fn_subsc     = ['_{x}','_{y}']
                fn_units     = '(m)'
                plotNr      += 1

                in_Tfs       = True
                M_optfn_x    = madx.GetColumn('DX')
                M_optfn_y    = madx.GetColumn('DY')
                B_optfn_x    = bdata.Disp_x()
                B_optfn_y    = bdata.Disp_y()
                PTC_optfn_x  = ptcdata.Disp_x()
                PTC_optfn_y  = ptcdata.Disp_y()
                PTC_opterr_x = 0 #error calculations for dispersion not implemented yet
                PTC_opterr_y = 0
                B_opterr_x   = bdata.Sigma_disp_x()
                B_opterr_y   = bdata.Sigma_disp_y()
                
            elif (opt=='dispersion_xpyp'):
                fn_name      = r'D' #this is a raw string for Latex labels and titles
                fn_rname     = 'dispersion_xpyp'   #this is reduced name for filename of saved figure
                fn_subsc     = ['_{xp}','_{yp}']
                fn_units     = '(rad)'
                plotNr      += 1

                print "Warning: Disp_xpyp not present in MADX tfs file, plotting only MADX-PTC and BDSIM results "
                in_Tfs       = False
                #M_optfn_x   = madx.GetColumn('DXP')
                #M_optfn_y   = madx.GetColumn('DYP')
                B_optfn_x    = bdata.Disp_xp()
                B_optfn_y    = bdata.Disp_yp()
                PTC_optfn_x  = ptcdata.Disp_xp()
                PTC_optfn_y  = ptcdata.Disp_yp()
                PTC_opterr_x = 0 #error calculations for dispersion not implemented yet
                PTC_opterr_y = 0
                B_opterr_x   = bdata.Sigma_disp_xp()
                B_opterr_y   = bdata.Sigma_disp_yp()
            else:
                print "Error: Unrecognised plotting option:", plot
                return
            
            #   if(in_Tfs):  
            #       M_s    = M_s[:len(B_s)]
            #       M_optfn_x = M_optfn_x[:len(B_optfn_x)]    #Madx arrays need to be sliced because they contain
            #       M_optfn_y = M_optfn_y[:len(B_optfn_y)]    #one too many columns. No information is lost in the slicing
            #as the last Madx segment is default end of the line info and is
            #degenerate with the last element segment
            #  PTC_s    = PTC_s[:len(B_s)]
            #  PTC_optfn_x = PTC_optfn_x[:len(B_optfn_x)]
            #  PTC_optfn_y = PTC_optfn_y[:len(B_optfn_y)]
        
            _plt.figure(self.figureNr+plotNr-2, figsize=(13, 8), dpi=80, facecolor='w', edgecolor='k')
            _plt.clf()
            _plt.plot([], [], color='w', linewidth=0.001,alpha=0.1,label=r'Npart= '+str(self.nparticles))
            if(in_Tfs):
                _plt.plot(M_s,M_optfn_x,'.',color='r',linestyle='dashed',linewidth=2.0,label=r'$'+fn_name+fn_subsc[0]+r'$MDX')
                _plt.plot(M_s,M_optfn_y,'.',color='b',linestyle='dashed',linewidth=2.0,label=r'$'+fn_name+fn_subsc[1]+r'$MDX')
            _plt.fill_between(PTC_s, PTC_optfn_x-PTC_opterr_x, PTC_optfn_x+PTC_opterr_x,alpha=0.3, facecolor='r',linewidth=0.0)
            _plt.fill_between(PTC_s, PTC_optfn_y-PTC_opterr_y, PTC_optfn_y+PTC_opterr_y,alpha=0.3, facecolor='b',linewidth=0.0)
            _plt.errorbar(B_s,B_optfn_x, yerr=B_opterr_x,fmt='o',color='r',label=r'$'+fn_name+fn_subsc[0]+r'$BDS')
            _plt.errorbar(B_s,B_optfn_y, yerr=B_opterr_y,fmt='o',color='b',label=r'$'+fn_name+fn_subsc[1]+r'$BDS')
            _plt.plot([], [], color='r', linewidth=10,alpha=0.3,label=r'$'+fn_name+fn_subsc[0]+r'$PTC')
            _plt.plot([], [], color='b', linewidth=10,alpha=0.3,label=r'$'+fn_name+fn_subsc[1]+r'$PTC')
            _plt.xlabel(r'$S (m)$')
            _plt.ylabel(r'$'+fn_name+fn_units+r'$')
            _plt.legend(numpoints=1,loc=7,fancybox=True, framealpha=0.5,prop={'size':15})
            _plt.grid(True)
            pybdsim.Plot.AddMachineLatticeToFigure(_plt.gcf(),''+self.tfsfilename+'.tfs')
            _plt.subplots_adjust(left=0.1,right=0.9,top=0.96, bottom=0.15, wspace=0.15, hspace=0.2)

        if showResiduals:
            #optical function residuals
            """
            if(in_Tfs):
                res_optfn_x = M_optfn_x-B_optfn_x        
                res_optfn_y = M_optfn_y-B_optfn_y
            
                _plt.figure(self.figureNr+1, figsize=(11, 8), dpi=80, facecolor='w', edgecolor='k')
                _plt.clf()
                _plt.plot(M_s,res_optfn_x,'*',color='r',linestyle='solid',label=r'$\beta_{x}$Res')
                _plt.plot(M_s,res_optfn_y,'*',color='b',linestyle='solid',label=r'$\beta_{y}$Res')
                _plt.title(self.filename+r' Plot of $'+fn_name+r'_{x,y}$ Residuals vs $S$')
                _plt.xlabel(r'$S (m)$')
                _plt.ylabel(r'$'+fn_name+r'_{x,y}$ Residuals(m)')
                _plt.legend(numpoints=1,loc=7,prop={'size':15})
                _plt.grid(True)
            """
                   
            # 2d plots
            arrow_width_scale = 1e-3  #Factor used to multiply minimum residual between BDSIM and PTC data in order to
                                      #heuristicaly obtain a width for the quiver plot arrows connecting the two data sets
                                      #Very crude, fix in the future

            #Scatter plots with quiver plots underneath. Useful visualising distributions of low number of particles, ignore for many particles
            if(self.nparticles<300):
                f = _plt.figure(self.figureNr+2, figsize=(13, 8), dpi=80, facecolor='w', edgecolor='k')
                f.suptitle(self.filename)
                _plt.clf()
                #X vs Y
                ax1 = f.add_subplot(221)
                arrow_width = abs(_np.min(fresy))*arrow_width_scale
                _plt.quiver(Mx,My,-fresx,-fresy,angles='xy',scale_units='xy',scale=1,color='r',units='x',width=arrow_width,headwidth=3)
                _plt.plot(Mx,My,'b.',label='PTC')
                _plt.plot(Bx,By,'g.',label='BDSIM')
                if addPrimaries:
                    _plt.plot(Bx0,By0,'r.',label='BDSIM prim')
                _plt.legend(prop={'size':10})
                _plt.xlabel(r"x (m)")
                _plt.ylabel(r"y (m)")
                startx, endx = ax1.get_xlim()
                starty, endy = ax1.get_ylim()
                ax1.xaxis.set_ticks([startx,0,endx])
                ax1.yaxis.set_ticks([starty,0,endy])
                locs,labels = _plt.xticks()
                _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
                locs,labels = _plt.yticks()
                _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
                ax1.tick_params(axis='both', which='major', pad=7)

                #XP vs YP
                ax2 = f.add_subplot(222)
                arrow_width = abs(_np.min(fresyp))*arrow_width_scale
                _plt.quiver(Mxp,Myp,-fresxp,-fresyp,angles='xy',scale_units='xy',scale=1,color='r',units='x',width=arrow_width,headwidth=3)
                _plt.plot(Mxp,Myp,'b.',label='PTC')
                _plt.plot(Bxp,Byp,'g.',label='BDSIM')
                if addPrimaries:
                    _plt.plot(Bxp0,Byp0,'r.',label='BDSIM prim')
                _plt.legend(prop={'size':10})
                _plt.xlabel(r"xp (rad)")
                _plt.ylabel(r"yp (rad)")
                startx, endx = ax2.get_xlim()
                starty, endy = ax2.get_ylim()
                ax2.xaxis.set_ticks([startx,0,endx])
                ax2.yaxis.set_ticks([starty,0,endy])
                locs,labels = _plt.xticks()
                _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
                locs,labels = _plt.yticks()
                _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
                ax2.tick_params(axis='both', which='major', pad=7)
                        
                #X vs XP
                arrow_width = abs(_np.min(fresxp))*arrow_width_scale
                ax3 = f.add_subplot(223)
                _plt.quiver(Mx,Mxp,-fresx,-fresxp,angles='xy',scale_units='xy',scale=1,color='r',units='x',width=arrow_width,headwidth=3)
                _plt.plot(Mx,Mxp,'b.',label='PTC')
                _plt.plot(Bx,Bxp,'g.',label='BDSIM')
                if addPrimaries:
                    _plt.plot(Bx0,Bxp0,'r.',label='BDSIM prim')
                _plt.legend(prop={'size':10})
                _plt.xlabel(r"x (m)")
                _plt.ylabel(r"xp (rad)")
                startx, endx = ax3.get_xlim()
                starty, endy = ax3.get_ylim()
                ax3.xaxis.set_ticks([startx,0,endx])
                ax3.yaxis.set_ticks([starty,0,endy])
                locs,labels = _plt.xticks()
                _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
                locs,labels = _plt.yticks()
                _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
                ax3.tick_params(axis='both', which='major', pad=7)
                    
                #Y vs YP
                arrow_width = abs(_np.min(fresyp))*arrow_width_scale
                ax4 = f.add_subplot(224)
                _plt.quiver(My,Myp,-fresy,-fresyp,angles='xy',scale_units='xy',scale=1,color='r',units='x',width=arrow_width,headwidth=3)
                _plt.plot(My,Myp,'b.',label='PTC')
                _plt.plot(By,Byp,'g.',label='BDSIM')
                if addPrimaries:
                    _plt.plot(By0,Byp,'r.',label='BDSIM prim')
                _plt.legend(prop={'size':10})
                _plt.xlabel(r"y (m)")
                _plt.ylabel(r"yp (rad)")
                startx, endx = ax4.get_xlim()
                starty, endy = ax4.get_ylim()
                ax4.xaxis.set_ticks([startx,0,endx])
                ax4.yaxis.set_ticks([starty,0,endy])
                locs,labels = _plt.xticks()
                _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
                locs,labels = _plt.yticks()
                _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
                ax4.tick_params(axis='both', which='major', pad=7)

                _plt.subplots_adjust(left=0.1,right=0.9,top=0.95, bottom=0.15, wspace=0.35, hspace=0.3)
            
                # 1d plots
                # x comparison
                f = _plt.figure(self.figureNr+6, figsize=(11, 8), dpi=80, facecolor='w', edgecolor='k')
                f.suptitle(self.filename)
                _plt.clf()

                nbinsx = _np.linspace(min(Mx),max(Mx),10)    #fix bins to avoid potential underflow/overflow
                nbinsy = _np.linspace(min(My),max(My),10)
                nbinsxp = _np.linspace(min(Mxp),max(Mxp),10)
                nbinsyp = _np.linspace(min(Myp),max(Myp),10)
                
                ax1 = f.add_subplot(221)
                ax1.hist(Mx,nbinsx,color='b',label='PTC',histtype='step')
                ax1.hist(Bx,nbinsx,color='g',label='BDSIM',histtype='step')
                if addPrimaries:
                    ax1.hist(Bx0,nbinsx,color='r',label='BDSIM prim',histtype='step')
                ax1.legend(fontsize='x-small',loc=0)
                ax1.set_xlabel(r"x (m)")
                startx, endx = ax1.get_xlim()
                starty, endy = ax1.get_ylim()
                ax1.xaxis.set_ticks([startx,0,endx])
                ax1.yaxis.set_ticks([starty,0,endy])
                
            
                # y comparison
                ax2 = f.add_subplot(222)
                ax2.hist(My,nbinsy,color='b',label='PTC',histtype='step')
                ax2.hist(By,nbinsy,color='g',label='BDSIM',histtype='step')
                if addPrimaries:
                    ax2.hist(By0,nbinsy,color='r',label='BDSIM prim',histtype='step')
                ax2.legend(fontsize='x-small',loc=0)
                ax2.set_xlabel(r"y (m)")
                startx, endx = ax2.get_xlim()
                starty, endy = ax2.get_ylim()
                ax2.xaxis.set_ticks([startx,0,endx])
                ax2.yaxis.set_ticks([starty,0,endy])

                # xp comparison
                ax3 = f.add_subplot(223)
                ax3.hist(Mxp,nbinsxp,color='b',label='PTC',histtype='step')
                ax3.hist(Bxp,nbinsxp,color='g',label='BDSIM',histtype='step')
                if addPrimaries:
                    ax3.hist(Bxp0,nbinsxp,color='r',label='BDSIM prim',histtype='step')
                ax3.legend(fontsize='x-small',loc=0)
                ax3.set_xlabel(r"x' (rad)")
                startx, endx = ax3.get_xlim()
                starty, endy = ax3.get_ylim()
                ax3.xaxis.set_ticks([startx,0,endx])
                ax3.yaxis.set_ticks([starty,0,endy])

                # yp comparison
                ax4 = f.add_subplot(224)
                ax4.hist(Myp,nbinsyp,color='b',label='PTC',histtype='step')
                ax4.hist(Byp,nbinsyp,color='g',label='BDSIM',histtype='step')
                if addPrimaries:
                    ax4.hist(Byp0,nbinsyp,color='r',label='BDSIM prim',histtype='step')
                ax4.legend(fontsize='x-small',loc=0)
                ax4.set_xlabel(r"y' (rad)")
                startx, endx = ax4.get_xlim()
                starty, endy = ax4.get_ylim()
                ax4.xaxis.set_ticks([startx,0,endx])
                ax4.yaxis.set_ticks([starty,0,endy])
            
                _plt.subplots_adjust(left=0.1,right=0.9,top=0.95, bottom=0.15, wspace=0.3, hspace=0.2)

            """
            # residuals in one plot
            nbins=50
            
            f = _plt.figure(self.figureNr+10, figsize=(13, 8), dpi=80, facecolor='w', edgecolor='k')
            _plt.clf()

            axX = f.add_subplot(221)
            hist, xedges, yedges = _np.histogram2d(Mx,fresx,bins=nbins)
            hist = _np.rot90(hist)                         #flip and rotate the plots to display them properly
            hist = _np.flipud(hist)
            histmasked = _np.ma.masked_where(hist==0,hist) # Mask pixels with a value of zero
            
            _plt.pcolormesh(xedges,yedges,histmasked)
            axX.set_xlabel('x(m)')
            axX.set_ylabel('$Residuals_{x}$(m)')
            cbar = _plt.colorbar()
            cbar.ax.set_ylabel('Counts')
            startx, endx = axX.get_xlim()
            starty, endy = axX.get_ylim()
            axX.xaxis.set_ticks([startx,0,endx])
            axX.yaxis.set_ticks([starty,0,endy])
            
            axX = f.add_subplot(222)
            hist, xedges, yedges = _np.histogram2d(My,fresy,bins=nbins)
            hist = _np.rot90(hist)
            hist = _np.flipud(hist)
            histmasked = _np.ma.masked_where(hist==0,hist)
            
            _plt.pcolormesh(xedges,yedges,histmasked)
            axX.set_xlabel('y(m)')
            axX.set_ylabel('$Residuals_{y}$(m)')
            cbar = _plt.colorbar()
            cbar.ax.set_ylabel('Counts')
            startx, endx = axX.get_xlim()
            starty, endy = axX.get_ylim()
            axX.xaxis.set_ticks([startx,0,endx])
            axX.yaxis.set_ticks([starty,0,endy])
            
            axX = f.add_subplot(223)
            hist, xedges, yedges = _np.histogram2d(Mxp,fresxp,bins=nbins)
            hist = _np.rot90(hist)
            hist = _np.flipud(hist)
            histmasked = _np.ma.masked_where(hist==0,hist)
            
            _plt.pcolormesh(xedges,yedges,histmasked)
            axX.set_xlabel('xp(rad)')
            axX.set_ylabel('$Residuals_{xp}$(rad)')
            cbar = _plt.colorbar()
            cbar.ax.set_ylabel('Counts')
            startx, endx = axX.get_xlim()
            starty, endy = axX.get_ylim()
            axX.xaxis.set_ticks([startx,0,endx])
            axX.yaxis.set_ticks([starty,0,endy])
            
            axX = f.add_subplot(224)
            hist, xedges, yedges = _np.histogram2d(Myp,fresyp,bins=nbins)
            hist = _np.rot90(hist)
            hist = _np.flipud(hist)
            histmasked = _np.ma.masked_where(hist==0,hist)
            
            _plt.pcolormesh(xedges,yedges,histmasked)
            axX.set_xlabel('yp(rad)')
            axX.set_ylabel('$Residuals_{yp}$(rad)')
            cbar = _plt.colorbar()
            cbar.ax.set_ylabel('Counts')
            startx, endx = axX.get_xlim()
            starty, endy = axX.get_ylim()
            axX.xaxis.set_ticks([startx,0,endx])
            axX.yaxis.set_ticks([starty,0,endy])

            _plt.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.15, wspace=0.39, hspace=0.3)
            """

            f = _plt.figure(self.figureNr+10, figsize=(13, 8), dpi=80, facecolor='w', edgecolor='k')
            _plt.clf()

            ax1 = f.add_subplot(221)

            binned    = binned_statistic(Mx,fresx, 'mean', bins=15 )
            bin_means = binned[0]
            bin_edges = binned[1]
            bin_std   = binned_statistic(Mx, fresx, _np.std, bins=15)[0] 
            bin_count = binned_statistic(Mx, fresx, 'count', bins=15)[0]
            bin_err   = _np.nan_to_num(bin_std/_np.sqrt(bin_count))
            
            ax1.bar(bin_edges[:-1], bin_means, 0.85*(bin_edges[1]-bin_edges[0]), yerr=bin_err, color='b',ec='b',alpha=0.5)
            ax1.set_xlim([min(Mx),max(Mx)])
            startx, endx = ax1.get_xlim()
            starty, endy = ax1.get_ylim()
            ax1.xaxis.set_ticks([startx,0,endx])
            ax1.yaxis.set_ticks([starty,0,endy])
            locs,labels = _plt.xticks()
            _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
            locs,labels = _plt.yticks()
            _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
            ax1.tick_params(axis='both', which='major', pad=7)
            ax1.set_xlabel('x(m)')
            ax1.set_ylabel('x residuals(m)')

            ax2 = f.add_subplot(222)

            binned    = binned_statistic(My,fresy, 'mean', bins=15 )
            bin_means = binned[0]
            bin_edges = binned[1]
            bin_std   = binned_statistic(My, fresy, _np.std, bins=15)[0] 
            bin_count = binned_statistic(My, fresy, 'count', bins=15)[0]
            bin_err   = _np.nan_to_num(bin_std/_np.sqrt(bin_count))
            
            ax2.bar(bin_edges[:-1], bin_means, 0.85*(bin_edges[1]-bin_edges[0]), yerr=bin_err, color='r',ec='r',alpha=0.5)
            ax2.set_xlim([min(My),max(My)])
            startx, endx = ax2.get_xlim()
            starty, endy = ax2.get_ylim()
            ax2.xaxis.set_ticks([startx,0,endx])
            ax2.yaxis.set_ticks([starty,0,endy])
            locs,labels = _plt.xticks()
            _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
            locs,labels = _plt.yticks()
            _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
            ax2.tick_params(axis='both', which='major', pad=7)
            ax2.set_xlabel('y(m)')
            ax2.set_ylabel('y residuals(m)')
            
            ax3 = f.add_subplot(223)

            binned    = binned_statistic(Mxp,fresxp, 'mean', bins=15 )
            bin_means = binned[0]
            bin_edges = binned[1]
            bin_std   = binned_statistic(Mxp, fresxp, _np.std, bins=15)[0] 
            bin_count = binned_statistic(Mxp, fresxp, 'count', bins=15)[0]
            bin_err   = _np.nan_to_num(bin_std/_np.sqrt(bin_count))
            
            ax3.bar(bin_edges[:-1], bin_means, 0.85*(bin_edges[1]-bin_edges[0]), yerr=bin_err, color='g',ec='g',alpha=0.5)
            ax3.set_xlim([min(Mxp),max(Mxp)])
            startx, endx = ax3.get_xlim()
            starty, endy = ax3.get_ylim()
            ax3.xaxis.set_ticks([startx,0,endx])
            ax3.yaxis.set_ticks([starty,0,endy])
            locs,labels = _plt.xticks()
            _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
            locs,labels = _plt.yticks()
            _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
            ax3.tick_params(axis='both', which='major', pad=7)
            ax3.set_xlabel('xp(rad)')
            ax3.set_ylabel('xp residuals(rad)')

            ax4 = f.add_subplot(224)

            binned    = binned_statistic(Myp,fresyp, 'mean', bins=15 )
            bin_means = binned[0]
            bin_edges = binned[1]
            bin_std   = binned_statistic(Myp, fresyp, _np.std, bins=15)[0] 
            bin_count = binned_statistic(Myp, fresyp, 'count', bins=15)[0]
            bin_err   = _np.nan_to_num(bin_std/_np.sqrt(bin_count))
            print "total entries=",sum(bin_count),"bin counts= ", bin_count,"bin means= ", bin_means, "bin std= ", bin_err
            
            ax4.bar(bin_edges[:-1], bin_means, 0.85*(bin_edges[1]-bin_edges[0]), yerr=bin_err, color='c',ec='c',alpha=0.5)
            ax4.set_xlim([min(Myp),max(Myp)])
            startx, endx = ax4.get_xlim()
            starty, endy = ax4.get_ylim()
            ax4.xaxis.set_ticks([startx,0,endx])
            ax4.yaxis.set_ticks([starty,0,endy])
            locs,labels = _plt.xticks()
            _plt.xticks(locs, map(lambda x: "%2.1e" % x, locs))
            locs,labels = _plt.yticks()
            _plt.yticks(locs, map(lambda x: "%2.1e" % x, locs))
            ax4.tick_params(axis='both', which='major', pad=7)
            ax4.set_xlabel('yp(rad)')
            ax4.set_ylabel('yp residuals(rad)')

            _plt.subplots_adjust(left=0.15,right=0.95,top=0.95,wspace=0.39,hspace=0.25)

            #print emittance
            print 'Horizontal emittance bdsim (before,after) ',bdata.Emitt_x()
            print 'Vertical emittance bdsim (before,after) ',bdata.Emitt_y()

            #print stdev fractional errors
            print 'stdFracErrX= ',frestdx,' stdFracErrY= ', frestdy, 'stdFracErrXP= ', frestdxp, 'stdFracErrX= ', frestdyp

            if(showPlots):
                _plt.show()

        #Open pdf output file and save all plots to it
        pdf = matplotlib.backends.backend_pdf.PdfPages(self.filename+"_plots.pdf")
        for i in _plt.get_fignums():
            pdf.savefig(i)
        pdf.close()
        



       

        

            

        
            


        

    

