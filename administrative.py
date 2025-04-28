# HALLINTASOVELLUKSEN PÄÄIKKUNAN JA DIALOGIEN KOODI
# =================================================

# KIRJASTOJEN JA MODUULIEN LATAUKSET
# ----------------------------------

# Pythonin sisäiset moduulit
import os # Polkumääritykset
import sys # Käynnistysargumentit
import json # JSON-objektien ja tiedostojen käsittely

# Asennuksen vaativat kirjastot
from PySide6 import QtWidgets # Qt-vimpaimet
from PySide6 import QtGui # Pixmap-muutoksia varten ja Web sivujen näyttö
from PySide6.QtCore import QDate, QUrl # Päivämäärät ja URL-osoitteet


# Käyttöliittymämoduulien lataukset
from administrative_ui import Ui_MainWindow # Käännetyn käyttöliittymän luokka
from settingsDialog_ui import Ui_Dialog as Settings_Dialog # Asetukset-dialogin luokka
from aboutDialog_ui import Ui_Dialog as About_Dialog

# Omat moduulit
from lendingModules import cipher # Salakirjoitusmoduuli
from lendingModules import dbOperations # PostgreSQL-tietokantayhteydet
from lendingModules import barcode # Viivakoodin muodostaminen (varmiste)


# LUOKKAMÄÄRITYKSET
# -----------------

# Määritellään pääikkunan luokka, joka perii QMainWindow- ja Ui_MainWindow-luokan
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """A class for creating main window for the application"""
    
    # Määritellään olionmuodostin ja kutsutaan yliluokkien muodostimia
    def __init__(self):
        super().__init__()

        # Luodaan käyttöliittymä konvertoidun tiedoston perusteella MainWindow:n ui-ominaisuudeksi. Tämä suojaa lopun MainWindow-olion ylikirjoitukselta, kun ui-tiedostoa päivitetään
        self.ui = Ui_MainWindow()

        # Kutsutaan käyttöliittymän muodostusmetodia setupUi
        self.ui.setupUi(self)

        # Rutiini, joka lukee asetukset, jos ne ovat olemassa
        try:
            # Avataam asetustiedosto ja muutetaan se Python sanakirjaksi
            with open('settings.json', 'rt') as settingsFile: # With sulkee tiedoston automaattisesti
                
                jsonData = settingsFile.read()
                self.currentSettings = json.loads(jsonData)

            # Puretaan salasana tietokannan käyttöä varten
            self.plainTextPassword = cipher.decryptString(self.currentSettings['password'])

            # Huom! Salasana pitää tallentaa JSON-tiedostoon tavallisena merkkijonona, ei byte string muodossa. Salauskirjaston decode ja encode metodit hoitavat asian

            # Päivitetään käyttöliittymäelementtien tiedot tietokannasta
            self.refreshUi()

              
        except Exception as e:
            self.openSettingsDialog()

        # Asetetaan auton oletuskuvaksi harmaa kamera
        self.vehiclePicture = 'uiPictrues\\noPicture.png'

        # Poistettavien tietojen avaimet
        self.vehicleToModify = ''
        self.personToModify = ''
        self.vehicleTypeToModify = ''
        self.reasonToModify = ''

        # Kuluvan päivän ja vuoden määritys
        self.today = QDate.currentDate()
        self.currentYear = str(self.today.toPython())[0:4]
        self.firstDayOfYear = QDate(int(self.currentYear), 1, 1)

        # OHJELMOIDUT SIGNAALIT
        # ---------------------
        
        # Valikkotoiminnot
        self.ui.actionMuokkaa.triggered.connect(self.openSettingsDialog)
        self.ui.actionTietoja_ohjelmasta.triggered.connect(self.openAboutDialog)
        self.ui.actionOhjesivut.triggered.connect(self.openWebHelp)

        # Välilehtien vaihdon käynistämät singnaalit

        # Kun välilehteä vaihdetaan, päivitetään yhdistelmäruutujen valinnat
        self.ui.tabWidget.currentChanged.connect(self.updateChoices)

        # Painikkeet
        self.ui.savePersonPushButton.clicked.connect(self.savePerson)
        self.ui.saveVehiclePushButton.clicked.connect(self.saveVehicle)
        self.ui.openPicturePushButton.clicked.connect(self.openPicture)
        self.ui.deleteVehiclePushButton.clicked.connect(self.deleteVehicle)
        self.ui.deletePersonPushButton.clicked.connect(self.deletePerson)
        self.ui.getReportPushButton.clicked.connect(self.updateDiaryTableWidget) #Ajopäiväkirjojen haku
        self.ui.notUsableVehiclePushButton.clicked.connect(self.setNotLendable)
        self.ui.reasonAddPushButton.clicked.connect(self.newReason)
        self.ui.reasonRemovePushButton.clicked.connect(self.deleteReason)
        self.ui.vehicleTypeAddPushButton.clicked.connect(self.newVehicleType)
        self.ui.vehicleTypeRemovePushButton.clicked.connect(self.deleteVehicleType)

        # Painikeidden aktivoinnit syöttökentistä poistuttaessa
        self.ui.capacityLineEdit.textChanged.connect(self.showSaveVehiclePB)
        self.ui.vehicleClassLineEdit.textChanged.connect(self.showSavePersonPB)
        self.ui.vehicleTypeAddLineEdit.textChanged.connect(self.showVehicleAddPB)
        self.ui.reasonAddLineEdit.textChanged.connect(self.showReasonAddPB)

        # Painikkeiden deaktivointi kun aloitetaan ensimmäisen lomakekentän muokkaaminen
        self.ui.ssnLineEdit.textChanged.connect(self.hideDeletePersonPB)
        self.ui.numberPlateLineEdit.textChanged.connect(self.hideVehicleButtons)


        # Taulukko soluvalinnat
        self.ui.vehicleCatalogTableWidget.cellClicked.connect(self.setRegisterNumber)
        self.ui.registeredPersonsTableWidget.cellClicked.connect(self.setSNN)
        self.ui.vehicleTypeAddTableWidget.cellClicked.connect(self.setVehicleType)
        self.ui.reasonAddTableWidget.cellClicked.connect(self.setReason)

        # Kenttien muuntaminen isoille alkukirjaimille ja isoille kirjaimille
        self.ui.ssnLineEdit.editingFinished.connect(self.makeUpperCaze)
        self.ui.vehicleClassLineEdit.editingFinished.connect(self.makeUpperCaze)
        self.ui.numberPlateLineEdit.editingFinished.connect(self.makeUpperCaze)
        self.ui.firstNameLineEdit.editingFinished.connect(self.makeFristCharUpperCase)
        self.ui.lastNameLineEdit.editingFinished.connect(self.makeFristCharUpperCase)
        self.ui.manufacturerLineEdit.editingFinished.connect(self.makeFristCharUpperCase)
        self.ui.modelLineEdit.editingFinished.connect(self.makeFristCharUpperCase)
        self.ui.vehicleOwnerLineEdit.editingFinished.connect(self.makeFristCharUpperCase)
        
    # OHJELMOIDUT SLOTIT
    # ==================

    # DIALOGIEN AVAUSMETODIT
    # ----------------------

    # Valikkotoimintojen slotit
    # -------------------------

    # Asetusdialogin avaus
    def openSettingsDialog(self):
        self.saveSettingsDialog = SaveSettingsDialog() # Luodaan luokasta olio
        self.saveSettingsDialog.setWindowTitle('Palvelinasetukset')
        self.saveSettingsDialog.exec() # Luodaan dialogille oma event loop
        
    # Tietoja ohjelmasta -dialogin avaus
    def openAboutDialog(self):
        url = QUrl('https://github.com/HennaSalla/Autolainaus_hallinta/blob/main/README.md')
        QtGui.QDesktopServices.openUrl(url)

    def openWebHelp(self):
        url = QUrl('https://github.com/HennaSalla/Autolainaus_hallinta/wiki/K%C3%A4ytt%C3%B6ohje')
        QtGui.QDesktopServices.openUrl(url)

    #Yleinen käyttöliitymän verestys (refresh)
    def refreshUi(self):
        # Auton kuvaksi kameran kuva
        self.vehiclePicture = 'uiPictrues\\noPicture.png' # Kuvan poluksi ei kuvaa symboli
        self.ui.vehiclePictureLabel.setPixmap(QtGui.QPixmap(self.vehiclePicture)) # Auton kuvan päivitys
        self.updateChoices() # Yhdistelmäruudun arvot
        self.updateLenderTableWidget() # Lainaajien tiedot
        self.updateVehicleTableWidget() # Autojen tiedot
        self.updateVehicleTypeAddTableWidget() # Autotyyppien ylläpidon taulukko
        self.updateReasonAddTableWidget() # Ajon syiden ylläpidon taulukko
        self.updateDiaryTableWidget() # Ajopäiväkirja
        self.ui.diaryTableWidget.clear() # Tyhjentää ajopäiväkirjan
        self.ui.deleteVehiclePushButton.setHidden(True) # Auton poisto-painike piiloon
        self.ui.deletePersonPushButton.setHidden(True) # Lainaajan poisto-painike piiloon
        self.ui.notUsableVehiclePushButton.setHidden(True) # Auton ei lainattavissa-painike piiloon
        self.ui.savePersonPushButton.setHidden(True) #Piilotetaan tallenna henkilö nappi
        self.ui.saveVehiclePushButton.setHidden(True) # Piilotetaan tallenna auto nappi
        self.ui.reasonAddLineEdit.clear() # Tyhjenetään kenttä ajon sysitä
        self.ui.vehicleTypeAddLineEdit.clear() # Tyhjenetään kenttä uusista ajoneuvotyypeistä
        self.ui.vehicleTypeAddPushButton.setHidden(True) # Piilotetaan lisää painike uusista ajoneuvotyypeistä
        self.ui.reasonAddPushButton.setHidden(True) # Piilotetaan lisää painike uusista ajon sysistä
        self.ui.vehicleTypeRemovePushButton.setHidden(True) # Piilotetaan poista painike uusista ajoneuvotyypeistä
        self.ui.reasonRemovePushButton.setHidden(True) # Piilotetaan poista painike uusista ajon syistä
        self.ui.endingDateEdit.setDate(self.today)
        self.ui.beginingDateEdit.setDate(self.firstDayOfYear)

    # Välilehtien slotit
    # ------------------

    # Valinta -ruudun arvojen päivitys
    def updateChoices(self):

        # Luetaan tietokanta-asetukset paikallisiin muuttujiin
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword # Vaihdetaan selväkieliseksi 

        # Päivitetään kuluva päivämäärä ja vuosi
        self.today = QDate.currentDate()
        self.currentYear = str(self.today.toPython())[0:4]
        self.firstDayOfYear = QDate(int(self.currentYear), 1, 1)

        # Tehdään lista ajoneuvotyypit-yhdistelmäruudun arvoista
        # Luodaan tietokanta yhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Tehdään lista ajoneuvotyyppi-listan arvoista
        typeList = dbConnection.readColumsFromTable('ajoneuvotyyppi', ['tyyppi'])
        typeStringList = []
        for item in typeList:
            stringValue = str(item[0])
            typeStringList.append(stringValue)
        self.ui.vehicleTypeComboBox.clear()
        self.ui.vehicleTypeComboBox.addItems(typeStringList)

        # Lista ajopäiväkirjoista -> raporttinäkymien nimet
        self.ui.reportTypecomboBox.clear()
        self.ui.reportTypecomboBox.addItems(['ajopaivakirja', 'autoittain'])

        # Raporttivälin päivämäärävalitsimen oletuspäivän asennukset
        self.ui.beginingDateEdit.setDate(self.firstDayOfYear)
        self.ui.endingDateEdit.setDate(self.today)


    # Lainaaja taulun päivittäminen
    def updateLenderTableWidget(self):
        # Luetaan tietokanta-asetukset paikallisiin muuttujiin
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword # Vaidetaan selväkieliseksi

        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Tehdään lista lainaaja-taulun tiedoista
        tableData = dbConnection.readAllColumnsFromTable('lainaaja')
        
        # Tyhjennetään vanhat tiedot käyttöliittymästä ennen uusien lukemista tietokannasta
        self.ui.registeredPersonsTableWidget.clearContents()

        # Määritellään taulukkoelementin otsikot
        headerRow = ['Henkilötunnus', 'Etunimi', 'Sukunimi', 'Ajokortti', 'Automaatti', 'sähköposti']
        self.ui.registeredPersonsTableWidget.setHorizontalHeaderLabels(headerRow)

        # Asetetaan taulukon solujen arvot
        for row in range(len(tableData)): # Luetaan listaa riveittäin
            for column in range(len(tableData[row])): # Luetaan monikkoa sarakkeittain
                
                # Muutetaan merkkijonoksi ja QTableWidgetItem-olioksi
                data = QtWidgets.QTableWidgetItem(str(tableData[row][column])) 
                self.ui.registeredPersonsTableWidget.setItem(row, column, data)

    # Autot-taulukon päivitys
    def updateVehicleTableWidget(self):
        # Luetaan tietokanta-asetukset paikallisiin muuttujiin
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword # Vaihdetaan selväkieliseksi 

        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Tehdään lista auto taulun tiedoista
        tableData = dbConnection.readAllColumnsFromTable('auto')

        # Tyhjenetään vanhat tiedot käyttöliitymästä ennen uusien lukemista
        self.ui.vehicleCatalogTableWidget.clearContents()

        # Määritellään taulukkoelementin otsikot
        headerRow = ['Rekisteri', 'Käytettävissä', 'Merkki', 'Malli', 'Vuosimalli', 'Henkilömäärä', 'Tyyppi', 'Automaatti', 'Vastuuhenkilö']
        self.ui.vehicleCatalogTableWidget.setHorizontalHeaderLabels(headerRow)

        # Asetetaan taulukon solujen arvot
        for row in range(len(tableData)): # Luetaan listaa riveittäin
            for column in range(len(tableData[row])): # Luetaan monikkoa sarakkeittain
                
                # Muutetaan merkkijonoksi ja QTableWidgetItem-olioksi
                data = QtWidgets.QTableWidgetItem(str(tableData[row][column])) 
                self.ui.vehicleCatalogTableWidget.setItem(row, column, data)


    # Päivitetään ajopäiväkirjan taulukko
    def updateDiaryTableWidget(self):
         # Luetaan tietokanta-asetukset paikallisiin muuttujiin
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword # Vaidetaan selväkieliseksi

        # Luetaan raportti-sivun kontrollit paikallisiin muuttujiin
        reportName = self.ui.reportTypecomboBox.currentText()
        dateStart = self.ui.beginingDateEdit.date().toPython()
        dateEnd = self.ui.endingDateEdit.date().toPython()
        userFilter = self.ui.ssnFilterLineEdit.text()
        registerFilter = self.ui.registerFilterLineEdit.text()
        reasonFilter = self.ui.reasonFilterLineEdit.text()
        sqlFilter = ''
        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)
        
        # Määritellään aikaväli, jolta raportti tulostetaan
        dateFilterSring = f"otto >= '{dateStart} 00:00:00+2' AND otto <= '{dateEnd} 23:59:59+2'"

        # Määritellään mahdollinen käyttäjäsuodatus
        if userFilter == '':
            userFilterString = ''
        else:
           userFilterString = f"AND hetu = '{userFilter}'"
            
        # Määritellään mahdollinen rekisterinumerosuodatus
        if registerFilter == '':
            registerFilterString = ''
        else:
            registerFilterString = f"AND rekisterinumero = '{registerFilter}'"

        # Määritellään mahdollinen ajontarkoitussuodatus
        if reasonFilter == '':
            reasonFilterString = ''
        else:
            reasonFilterString = f"AND tarkoitus = '{reasonFilter}'"

        # Lopullinen SQL-suodatin
        sqlFilter = dateFilterSring + userFilterString + registerFilterString + reasonFilterString
        tableData = dbConnection.filterColumsFromTable(reportName,['*'], sqlFilter)
    
        # Tyhjennetään vanhat tiedot käyttöliittymästä ennen uusien lukemista tietokannasta
        self.ui.diaryTableWidget.clearContents()

        # Määritellään taulukkoelementin otsikot
        headerRow = ['Rekisteri', 'Merkki', 'Malli', 'Tarkoitus', 'HeTu', 'Sukunimi', 'Etunimi', 'Otettu', 'Palautettu']
        self.ui.diaryTableWidget.setHorizontalHeaderLabels(headerRow)

        # Tulosjoukon rivimäärä
        numberOfRows = len(tableData)
        self.ui.diaryTableWidget.setRowCount(numberOfRows)

        # Asetetaan taulukon solujen arvot
        for row in range(len(tableData)): # Luetaan listaa riveittäin
            for column in range(len(tableData[row])): # Luetaan monikkoa sarakkeittain
                
                # Muutetaan merkkijonoksi ja QTableWidgetItem-olioksi
                data = QtWidgets.QTableWidgetItem(str(tableData[row][column])) 
                self.ui.diaryTableWidget.setItem(row, column, data)

    # Päivitetään Ajoneuvotyyppitaulukko
    def updateVehicleTypeAddTableWidget(self):
        # Luetaan tietokanta-asetukset paikallisiin muuttujiin
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword # Vaihdetaan selväkieliseksi 

        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Tehdään lista auto taulun tiedoista
        tableData = dbConnection.readAllColumnsFromTable('ajoneuvotyyppi')

        # Tyhjenetään vanhat tiedot käyttöliitymästä ennen uusien lukemista
        self.ui.vehicleTypeAddTableWidget.clearContents()

        # Määritellään taulukkoelementin otsikot
        headerRow = ['Ajoneuvotyyppi']
        self.ui.vehicleTypeAddTableWidget.setHorizontalHeaderLabels(headerRow)

        # Asetetaan taulukon solujen arvot
        for row in range(len(tableData)): # Luetaan listaa riveittäin
            for column in range(len(tableData[row])): # Luetaan monikkoa sarakkeittain
                
                # Muutetaan merkkijonoksi ja QTableWidgetItem-olioksi
                data = QtWidgets.QTableWidgetItem(str(tableData[row][column])) 
                self.ui.vehicleTypeAddTableWidget.setItem(row, column, data)

    # Päivitetään ajon tarkoitus taulukko
    def updateReasonAddTableWidget(self):
        # Luetaan tietokanta-asetukset paikallisiin muuttujiin
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword # Vaihdetaan selväkieliseksi 

        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Tehdään lista auto taulun tiedoista
        tableData = dbConnection.readAllColumnsFromTable('tarkoitus')

        # Tyhjenetään vanhat tiedot käyttöliitymästä ennen uusien lukemista
        self.ui.reasonAddTableWidget.clearContents()

        # Määritellään taulukkoelementin otsikot
        headerRow = ['Tarkoitus']
        self.ui.reasonAddTableWidget.setHorizontalHeaderLabels(headerRow)

        # Asetetaan taulukon solujen arvot
        for row in range(len(tableData)): # Luetaan listaa riveittäin
            for column in range(len(tableData[row])): # Luetaan monikkoa sarakkeittain
                
                # Muutetaan merkkijonoksi ja QTableWidgetItem-olioksi
                data = QtWidgets.QTableWidgetItem(str(tableData[row][column])) 
                self.ui.reasonAddTableWidget.setItem(row, column, data)


    # Syöttölomaketietojen tyhjennys
    # ------------------------------

    # Lainaaja tietojen tyhjennys
    def clearLenderData(self):
        self.ui.ssnLineEdit.clear()
        self.ui.firstNameLineEdit.clear()
        self.ui.lastNameLineEdit.clear()
        self.ui.vehicleClassLineEdit.clear()
        self.ui.manualCheckBox.setChecked(False)
        self.ui.emailLineEdit.clear()

    # Auton tietojen tyhjennys
    def clearVehicleData(self):
        self.ui.numberPlateLineEdit.clear()
        self.ui.manufacturerLineEdit.clear()
        self.ui.modelLineEdit.clear()
        self.ui.modelYearLineEdit.clear()
        self.ui.capacityLineEdit.clear()
        self.ui.manualCarCehckBox.setChecked(False)
        self.ui.vehicleOwnerLineEdit.clear()

    # Ajopäiväkirjarajausten tyhjennys
    def clearDiaryFilters(self):
        self.ui.ssnFilterLineEdit.clear()
        self.ui.registerFilterLineEdit.clear()
        self.ui.reasonFilterLineEdit.clear()

    # Lomakeiden syöttötietojen siistiminen
    def makeUpperCaze(self):
        self.ui.ssnLineEdit.setText(self.ui.ssnLineEdit.text().upper())
        self.ui.vehicleClassLineEdit.setText(self.ui.vehicleClassLineEdit.text().upper())
        self.ui.numberPlateLineEdit.setText(self.ui.numberPlateLineEdit.text().upper())

    def makeFristCharUpperCase(self):
        self.ui.firstNameLineEdit.setText(self.ui.firstNameLineEdit.text().title())
        self.ui.lastNameLineEdit.setText(self.ui.lastNameLineEdit.text().title())
        self.ui.manufacturerLineEdit.setText(self.ui.manufacturerLineEdit.text().title())
        self.ui.modelLineEdit.setText(self.ui.modelLineEdit.text().title())
        self.ui.vehicleOwnerLineEdit.setText(self.ui.vehicleOwnerLineEdit.text().title())

    # Painikkeiden slotit
    # -------------------

    # Auton tallennuspainikkeen näyttäminen
    def showSaveVehiclePB(self):
        self.ui.saveVehiclePushButton.setHidden(False)

    # Lainaajan tallenuspainikkeen näyttäminen
    def showSavePersonPB(self):
        self.ui.savePersonPushButton.setHidden(False)

    # Ajoneuvotyypit lisäyspainikkeen näyttäminen
    def showVehicleAddPB(self):
        self.ui.vehicleTypeAddPushButton.setHidden(False)

    #Ajon syyn lisäyspainikkeen näyttäminen
    def showReasonAddPB(self):
        self.ui.reasonAddPushButton.setHidden(False)

    # Piilotetaan ajoneuvon Poista- ja Ei käytettävissä -painikkeet  
    def hideVehicleButtons(self):
        self.ui.deleteVehiclePushButton.setHidden(True)
        self.ui.notUsableVehiclePushButton.setHidden(True)

    # Piilotetaan lainaajan poisto painike
    def hideDeletePersonPB(self):
        self.ui.deletePersonPushButton.setHidden(True)

    # Lainaajien tallennus
    def savePerson(self):
        # Määritellään tietokanta-asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword
        

        # Määritellään tallennusmetodin vaatimat parametrit
        tableName = 'lainaaja'
        ssn = self.ui.ssnLineEdit.text()
        email = self.ui.emailLineEdit.text()
        firstName = self.ui.firstNameLineEdit.text()
        lastName = self.ui.lastNameLineEdit.text()
        licenseType = self.ui.vehicleClassLineEdit.text()
        automaticGB = self.ui.manualCarCehckBox.isChecked()
        lenderDictionary = {'hetu': ssn,
                          'etunimi': firstName,
                          'sukunimi': lastName,
                          'ajokorttiluokka': licenseType,
                          'automaatti': automaticGB,
                          'sahkoposti': email
                          }
        
        
        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan tallennusmetodia
        try:
            dbConnection.addToTable(tableName, lenderDictionary)
            self.updateLenderTableWidget()
            self.ui.savePersonPushButton.setHidden(True) # Piilotetaan tallennus-painike
            statusBarMessage = f'Lainaajan {self.ui.lastNameLineEdit.text()} tiedot tallenettiin'
            self.ui.statusbar.showMessage(statusBarMessage, 5000)
            self.clearLenderData()

        except Exception as e:
            self.openWarning('Tallennus ei onnistunut', str(e)) 

    # Ajoneuvon kuvan lataaminen
    def openPicture(self):
        userPath = os.path.expanduser('~')
        pathToPictureFolder = userPath + '\\Pictures'
        fileName, check = QtWidgets.QFileDialog.getOpenFileName(None, 'Valitse auton kuva', pathToPictureFolder, 'Kuvat (*.png *.jpg)')
        
        # Jos kuvatiedosto on valittu
        if fileName:
            self.vehiclePicture = fileName

        vehiclePixmap = QtGui.QPixmap(self.vehiclePicture)
        self.ui.vehiclePictureLabel.setPixmap(vehiclePixmap)

    # Ajoneuvon tallennus
    def saveVehicle(self):
        # Määritellään tietokanta-asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword

        # Luetaan  syöttöelementtien arvot paikallisiin muutujiin
        numberPlate = self.ui.numberPlateLineEdit.text()
        manufacturer = self.ui.manufacturerLineEdit.text()
        model = self.ui.modelLineEdit.text()
        year = self.ui.modelYearLineEdit.text()
        capacity = int(self.ui.capacityLineEdit.text())
        vehicleType = self.ui.vehicleTypeComboBox.currentText()
        automaticGearBox = self.ui.manualCarCehckBox.isChecked()
        responsiblePerson = self.ui.vehicleOwnerLineEdit.text()

        # Määritellään tallennusmetodin vaatimat parametrit
        tableName = 'auto'
        vehicleDictionary = {'rekisterinumero': numberPlate,
                          'merkki': manufacturer,
                          'malli': model,
                          'vuosimalli': year,
                          'henkilomaara': capacity,
                          'tyyppi': vehicleType,
                          'automaatti': automaticGearBox,
                          'vastuuhenkilo': responsiblePerson}
        
        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan tallennusmetodia
        try:
            dbConnection.addToTable(tableName, vehicleDictionary)
            self.clearVehicleData()
        except Exception as e:
            self.openWarning('Tallennus ei onnistunut', str(e))
        
        # Luetaan kuvatiedostoa ja päivitetään autotaulua
        with open(self.vehiclePicture, 'rb') as pictureFile:
            pictureData = pictureFile.read()
        
        # Luodaan uusi yhteys, koska edellinen suljettiin
        dbConnection2 = dbOperations.DbConnection(dbSettings)

        try:
            dbConnection2.updateBinaryField('auto', 'kuva', 'rekisterinumero', f"'{numberPlate}'", pictureData)
            self.refreshUi()
        except Exception as e:
            self.openWarning('Kuvan päivitys ei onnistunut', str(e))

    def setNotLendable(self):
        # Määritellään tietokanta-asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword
        # Luodaan tietokantayhteys-olio
    
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan päivitysmetodia
        try:
            dbConnection.modifyTableData('auto', 'kaytettavissa', False, 'rekisterinumero', f"'{self.vehicleToModify}'")
            self.refreshUi()
        except Exception as e:
            self.openWarning('Auton tilaa ei saatu muutettua', str(e))

    # Poistetaan auto
    def deleteVehicle(self):
        # Määritellään tietokanta-asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword
        # Luodaan tietokantayhteys-olio
    
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan poistometodia

        try:
            dbConnection.deleteRowsFromTable('auto', 'rekisterinumero', f"'{self.vehicleToModify}'")
            self.refreshUi()
        except Exception as e:
            self.openWarning('Poisto ei onnistunut', str(e))

    # Poistetaan lainaaja
    def deletePerson(self):
        # Määritellään tietokanta-asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword
        # Luodaan tietokantayhteys-olio
    
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan poistometodia

        try:
            dbConnection.deleteRowsFromTable('lainaaja', 'hetu', f"'{self.personToDelete}'")
            self.refreshUi()
        except Exception as e:
            self.openWarning('Poisto ei onnistunut', str(e))

    # Uusi ajon tarkoitus tietokantaan
    def newReason(self):
        # Määritellään tietokanta asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword

        # Luetaan syöttöelementin arvot paikallisiin muutujiin
        reason = self.ui.reasonAddLineEdit.text()

        # Määritellään tallennusmetodin vaatimat parametrit
        tableName = 'tarkoitus'
        reasonDictionary = {'tarkoitus': reason}
        
        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan tallennusmetodia
        try:
            dbConnection.addToTable(tableName, reasonDictionary)
            self.refreshUi() # Päivitetään taulukko lisäyksen jälkeen
        except Exception as e:
            self.openWarning('Tallennus ei onnistunut', str(e))

    # Poistetaan ajon tarkoitus
    def deleteReason(self):
        # Määritellään tietokanta-asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword
        # Luodaan tietokantayhteys-olio
    
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan poistometodia

        try:
            dbConnection.deleteRowsFromTable('tarkoitus', 'tarkoitus', f"'{self.reasonToModify}'")
            self.refreshUi()
        except Exception as e:
            self.openWarning('Poisto ei onnistunut', str(e))

    # Luodaan uusi ajoneuvotyyppi
    def newVehicleType(self):
        pass
        # Määritellään tietokanta asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword

        # Luetaan syöttöelementin arvot paikallisiin muutujiin
        vehicleType = self.ui.vehicleTypeAddLineEdit.text()

        # Määritellään tallennusmetodin vaatimat parametrit
        tableName = 'ajoneuvotyyppi'
        newVehicleDictionary = {'tyyppi': vehicleType}
        
        # Luodaan tietokantayhteys-olio
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan tallennusmetodia
        try:
            dbConnection.addToTable(tableName, newVehicleDictionary)
            self.refreshUi() # Päivitetään taulukko lisäyksen jälkeen
        except Exception as e:
            self.openWarning('Tallennus ei onnistunut', str(e))

    # Poistetaan ajoneuvo tyyppi
    def deleteVehicleType(self):
        # Määritellään tietokanta-asetukset
        dbSettings = self.currentSettings
        plainTextPassword = self.plainTextPassword
        dbSettings['password'] = plainTextPassword
        # Luodaan tietokantayhteys-olio
    
        dbConnection = dbOperations.DbConnection(dbSettings)

        # Kutsutaan poistometodia

        try:
            dbConnection.deleteRowsFromTable('ajoneuvotyyppi', 'tyyppi', f"'{self.vehicleTypeToModify}'")
            self.refreshUi()
        except Exception as e:
            self.openWarning('Poisto ei onnistunut', str(e))

    # Taulukoiden soluvalinnat
    # ------------------------

    # Asetetaan poistetun auton rekisterinumero valitun rivin perusteella
    def setRegisterNumber(self):
        rowIndex = 0
        columnIndex = 0
        cellValue = ''

        # Haetaan aktiivisen rivin numero ja ensimäisen sarakeen arvo siltä riviltä
        rowIndex = self.ui.vehicleCatalogTableWidget.currentRow()
        cellValue = self.ui.vehicleCatalogTableWidget.item(rowIndex, columnIndex).text()
        self.vehicleToModify = cellValue
        self.ui.statusbar.showMessage(f'Valitun auton rekisterinumero on {cellValue}')
        self.ui.deleteVehiclePushButton.setHidden(False)
        self.ui.notUsableVehiclePushButton.setHidden(False)

    # Asetetaan poistetttavan henkilön HeTu valitun rivin perusteella
    def setSNN(self):
        rowIndex = 0
        columnIndex = 0
        cellValue = ''

        # Haetaan aktiivisen solun rivinumero ja ensimmäisen sarakkeen arvo siltä riviltä
        rowIndex = self.ui.registeredPersonsTableWidget.currentRow()
        cellValue = self.ui.registeredPersonsTableWidget.item(rowIndex, columnIndex).text()
        self.personToDelete = cellValue
        self.ui.statusbar.showMessage(f'valitun käyttäjän henkilötunnus on {cellValue}')
        self.ui.deletePersonPushButton.setHidden(False)

    # Asetetaan poistettavan ajoneuvotyypin arvo
    def setVehicleType(self):
        rowIndex = 0
        columnIndex = 0
        cellValue = ''

        # Haetaan aktiivisen rivin numero ja ensimäisen sarakeen arvo siltä riviltä
        rowIndex = self.ui.vehicleTypeAddTableWidget.currentRow()
        cellValue = self.ui.vehicleTypeAddTableWidget.item(rowIndex, columnIndex).text()
        self.vehicleTypeToModify = cellValue
        self.ui.statusbar.showMessage(f'Poistettava ajoneuvo tyyppi on {cellValue}')
        self.ui.vehicleTypeRemovePushButton.setHidden(False)
        self.ui.reasonRemovePushButton.setHidden(True)

    # Asetetaan poistettava ajon syy
    def setReason(self):
        rowIndex = 0
        columnIndex = 0
        cellValue = ''

        # Haetaan aktiivisen rivin numero ja ensimäisen sarakeen arvo siltä riviltä
        rowIndex = self.ui.reasonAddTableWidget.currentRow()
        cellValue = self.ui.reasonAddTableWidget.item(rowIndex, columnIndex).text()
        self.reasonToModify = cellValue
        self.ui.statusbar.showMessage(f'Poistettava ajon syy on {cellValue}')
        self.ui.reasonRemovePushButton.setHidden(False)
        self.ui.vehicleTypeRemovePushButton.setHidden(True)

    # Virheilmoitukset ja muut Message Box -dialogit
    # ----------------------------------------------

    # Malli mahdollista virheilmoitusta varten
    def openWarning(self, title: str, text: str) -> None:
        """Opens a message box for errors

        Args:
            title (str): The title of the message box
            text (str): Error message
        """
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Critical)
        msgBox.setWindowTitle(title)
        msgBox.setText('Tapahtui vakava virhe')
        msgBox.setDetailedText(text)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgBox.exec()

# Asetusten tallennusikkunan luokka
# ---------------------------------

class SaveSettingsDialog(QtWidgets.QDialog, Settings_Dialog):
    """A class to open settings dialog window"""
    
    # Määritellään olionmuodostin ja kutsutaan yliluokkien muodostimia
    def __init__(self):
        super().__init__()

        # Luodaan käyttöliittymä konvertoidun tiedoston perusteella MainWindow:n ui-ominaisuudeksi. Tämä suojaa lopun MainWindow-olion ylikirjoitukselta, kun ui-tiedostoa päivitetään
        self.ui = Settings_Dialog()

        # Kutsutaan käyttöliittymän muodostusmetodia setupUi
        self.ui.setupUi(self)
        
        # Luetaan asetustiedosto Python-sanakirjaksi
        self.currentSettings = {}

        # Tarkistetaan ensin, että asetustiedosto on olemassa
        try:
            with open('settings.json', 'rt') as settingsFile:
                jsonData = settingsFile.read()
                self.currentSettings = json.loads(jsonData)

            self.ui.serverLineEdit.setText(self.currentSettings['server'])
            self.ui.portLineEdit.setText(self.currentSettings['port'])
            self.ui.databaseLineEdit.setText(self.currentSettings['database'])
            self.ui.userLineEdit.setText(self.currentSettings['userName'])
            plaintextPassword = cipher.decryptString(self.currentSettings['password'])
            self.ui.passwordLineEdit.setText(plaintextPassword)
        except Exception as e:
            self.openInfo()
        

        # OHJELMOIDUT SIGNAALIT
        # ---------------------

        # Kun Tallenna-painiketta on klikattu, kutsutaan saveToJsonFile-metodia
        self.ui.saveSettingspushButton.clicked.connect(self.saveToJsonFile)

        # Sulje painikkeen toiminnot
        self.ui.closePushButton.clicked.connect(self.closeSettingsDialog)
    
    # OHJELMOIDUT SLOTIT (Luokan metodit)
    # -----------------------------------

    # Tallennetaan käyttöliittymään syötetyt asetukset tiedostoon
    def saveToJsonFile(self):

        # Luetaan käyttöliittymästä tiedot paikallisiin muuttujiin
        server = self.ui.serverLineEdit.text()
        port = self.ui.portLineEdit.text()
        database = self.ui.databaseLineEdit.text()
        userName = self.ui.userLineEdit.text()

        # Muutetaan merkkijono tavumuotoon (byte, merkistö UTF-8)
        plainTextPassword = self.ui.passwordLineEdit.text()
       
        # Salataan ja muunnetaan tavalliseksi merkkijonoksi, jotta JSON-tallennus onnistuu
        encryptedPassword = cipher.encryptString(plainTextPassword)

        # Muodostetaan muuttujista Python-sanakirja
        settingsDictionary = {
            'server': server,
            'port': port,
            'database': database,
            'userName': userName,
            'password': encryptedPassword
        }

        # Muunnetaan sanakirja JSON-muotoon
        jsonData = json.dumps(settingsDictionary)
        
        # Avataan asetustiedosto ja kirjoitetaan asetukset
        with open('settings.json', 'wt') as settingsFile:
            settingsFile.write(jsonData)

        # Suljetaan dialogin ikkuna
        self.close()

    def closeSettingsDialog(self):
        self.close()

    # Avataan MessageBox, jossa kerrotaan että tehdää uusi asetustiedosto
    def openInfo(self):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setWindowTitle('Luodaan uusi asetustiedosto')
        msgBox.setText('Syötä kaikkien kenttien tiedot ja käynnistä ohjelma uudestaan!')
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgBox.exec() # Luodaan Msg Box:lle oma event loop

# Avataan tietoja ohjelmasta ikkuna
# ---------------------------------

class AboutDialog(QtWidgets.QDialog, About_Dialog):
    """A class to show About dialog."""
    def __init__(self):
        super().__init__()

        # Luodaan käyttöliittymä konvertoidun tiedoston perusteella MainWindow:n ui-ominaisuudeksi. Tämä suojaa lopun MainWindow-olion ylikirjoitukselta, kun ui-tiedostoa päivitetään
        self.ui = About_Dialog()

        # Kutsutaan käyttöliittymän muodostusmetodia setupUi
        self.ui.setupUi(self)
    
if __name__ == "__main__":
    
    # Luodaan sovellus ja asetetaan tyyliksi Fusion
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('fusion')

    # Luodaan objekti pääikkunalle ja tehdään siitä näkyvä
    window = MainWindow()
    window.setWindowTitle('Autolainauksen hallinta')
    window.show()

    # Käynnistetään sovellus ja tapahtumienkäsittelijä
    app.exec()
    

    