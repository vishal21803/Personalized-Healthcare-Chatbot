import re
import pandas as pd
import pyttsx3
from sklearn import preprocessing
from sklearn.tree import DecisionTreeClassifier, _tree
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from sklearn.svm import SVC
import csv
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class MedicalChatBot:
    def __init__(self):
        self.training = pd.read_csv('Data/Training.csv')
        self.testing = pd.read_csv('Data/Testing.csv')
        self.cols = self.training.columns[:-1]
        self.x = self.training[self.cols]
        self.y = self.training['prognosis']
        self.y1 = self.y

        self.reduced_data = self.training.groupby(self.training['prognosis']).max()

        self.le = preprocessing.LabelEncoder()
        self.le.fit(self.y)
        self.y = self.le.transform(self.y)

        self.x_train, self.x_test, self.y_train, self.y_test = train_test_split(self.x, self.y, test_size=0.33, random_state=42)
        self.testx = self.testing[self.cols]
        self.testy = self.testing['prognosis']
        self.testy = self.le.transform(self.testy)

        self.clf = DecisionTreeClassifier()
        self.clf = self.clf.fit(self.x_train, self.y_train)

        self.model = SVC()
        self.model.fit(self.x_train, self.y_train)

        self.importances = self.clf.feature_importances_
        self.indices = np.argsort(self.importances)[::-1]
        self.features = self.cols

        self.severityDictionary = {}
        self.description_list = {}
        self.precautionDictionary = {}

        self.symptoms_dict = {}
        for index, symptom in enumerate(self.x):
            self.symptoms_dict[symptom] = index

    def readn(self, nstr):
        engine = pyttsx3.init()
        engine.setProperty('voice', "english+f5")
        engine.setProperty('rate', 130)
        engine.say(nstr)
        engine.runAndWait()
        engine.stop()

    def calc_condition(self, exp, days):
        sum = 0
        for item in exp:
            sum = sum + self.severityDictionary[item]
        if ((sum * days) / (len(exp) + 1) > 13):
            print("You should take the consultation from doctor. ")
        else:
            print("It might not be that bad but you should take precautions.")

    def getDescription(self):
        with open('MasterData/symptom_Description.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                self.description_list[row[0]] = row[1]

    def getSeverityDict(self):
        with open('MasterData/symptom_severity.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            try:
                for row in csv_reader:
                    self.severityDictionary[row[0]] = int(row[1])
            except:
                pass

    def getprecautionDict(self):
        with open('MasterData/symptom_precaution.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                self.precautionDictionary[row[0]] = [row[1], row[2], row[3], row[4]]

    def getInfo(self):
        print("-----------------------------------HealthCare ChatBot-----------------------------------")
        print("\nYour Name? \t\t\t\t", end="->")
        name = input("")
        print("Hello, ", name)

    def check_pattern(self, dis_list, inp):
        pred_list = []
        inp = inp.replace(' ', '_')
        patt = f"{inp}"
        regexp = re.compile(patt)
        pred_list = [item for item in dis_list if regexp.search(item)]
        if (len(pred_list) > 0):
            return 1, pred_list
        else:
            return 0, []

    def sec_predict(self, symptoms_exp):
        df = pd.read_csv('Data/Training.csv')
        X = df.iloc[:, :-1]
        y = df['prognosis']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=20)
        rf_clf = DecisionTreeClassifier()
        rf_clf.fit(X_train, y_train)

        symptoms_dict = {symptom: index for index, symptom in enumerate(X)}
        input_vector = np.zeros(len(symptoms_dict))
        for item in symptoms_exp:
            input_vector[[symptoms_dict[item]]] = 1

        return rf_clf.predict([input_vector])

    def print_disease(self, node):
        node = node[0]
        val = node.nonzero()
        disease = self.le.inverse_transform(val[0])
        return list(map(lambda x: x.strip(), list(disease)))

    def tree_to_code(self, tree, feature_names):
        tree_ = tree.tree_
        feature_name = [
            feature_names[i] if i != _tree.TREE_UNDEFINED else "undefined!"
            for i in tree_.feature
        ]

        chk_dis = ",".join(feature_names).split(",")
        symptoms_present = []

        while True:
            print("\nEnter the symptom you are experiencing  \t\t", end="->")
            disease_input = input("")
            conf, cnf_dis = self.check_pattern(chk_dis, disease_input)
            if conf == 1:
                print("searches related to input: ")
                for num, it in enumerate(cnf_dis):
                    print(num, ")", it)
                if num != 0:
                    print(f"Select the one you meant (0 - {num}):  ", end="")
                    conf_inp = int(input(""))
                else:
                    conf_inp = 0

                disease_input = cnf_dis[conf_inp]
                break
            else:
                print("Enter valid symptom.")

        while True:
            try:
                num_days = int(input("Okay. From how many days ? : "))
                break
            except:
                print("Enter valid input.")

        def recurse(node, depth):
            indent = "  " * depth
            if tree_.feature[node] != _tree.TREE_UNDEFINED:
                name = feature_name[node]
                threshold = tree_.threshold[node]

                if name == disease_input:
                    val = 1
                else:
                    val = 0
                if val <= threshold:
                    recurse(tree_.children_left[node], depth + 1)
                else:
                    symptoms_present.append(name)
                    recurse(tree_.children_right[node], depth + 1)
            else:
                present_disease = self.print_disease(tree_.value[node])
                red_cols = self.reduced_data.columns
                symptoms_given = red_cols[self.reduced_data.loc[present_disease].values[0].nonzero()]
                print("Are you experiencing any ")
                symptoms_exp = []
                for syms in list(symptoms_given):
                    inp = ""
                    print(syms, "? : ", end='')
                    while True:
                        inp = input("")
                        if (inp == "yes" or inp == "no"):
                            break
                        else:
                            print("provide proper answers i.e. (yes/no) : ", end="")
                    if (inp == "yes"):
                        symptoms_exp.append(syms)

                second_prediction = self.sec_predict(symptoms_exp)
                self.calc_condition(symptoms_exp, num_days)
                if (present_disease[0] == second_prediction[0]):
                    print("You may have ", present_disease[0])
                    print(self.description_list[present_disease[0]])
                else:
                    print("You may have ", present_disease[0], "or ", second_prediction[0])
                    print(self.description_list[present_disease[0]])
                    print(self.description_list[second_prediction[0]])

                precution_list = self.precautionDictionary[present_disease[0]]
                print("Take following measures : ")
                for i, j in enumerate(precution_list):
                    print(i + 1, ")", j)

        recurse(0, 1)

    def start_chat(self):
        self.getSeverityDict()
        self.getDescription()
        self.getprecautionDict()
        self.getInfo()
        self.tree_to_code(self.clf, self.cols)
        print("----------------------------------------------------------------------------------------")

if __name__ == "__main__":
    chatbot = MedicalChatBot()
    chatbot.start_chat()