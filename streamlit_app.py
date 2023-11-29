import streamlit as st
from pymongo import MongoClient
import bcrypt
from datetime import datetime, timedelta

# Connect to the MongoDB server
# Need to use streamlit secrets to hide this...
uri = "mongodb+srv://brodes02:ulLJgnhbeUIH0mFf@cluster0.dqzu3tl.mongodb.net/?retryWrites=true&w=majority"
# Initialize the mongodb client
client = MongoClient(uri)

# Access the database and subcollections that handle storage of characters and logins
LottoDB = client["LottoApp"]
UsersDB = LottoDB["users"]
TicketsDB = LottoDB["tickets"]
DrawingsDB = LottoDB["drawings"]
AdminDB = LottoDB["admin"]
WinnersDB = LottoDB["winners"]

# Initial conditions of session states that must be preserved
if "registering" not in st.session_state:
    st.session_state.registering = False
if "loggedIn" not in st.session_state:
    st.session_state.loggedIn = False
if "Username" not in st.session_state:
    st.session_state.Username = None
if "admin" not in st.session_state:
    st.session_state.admin = False
if "refreshReady" not in st.session_state:
    st.session_state.refreshReady = False
if "redeemingTicket" not in st.session_state:
    st.session_state.redeemingTicket = None

# This helper function can be used as a callback on buttons to update states if you need to.
# Takes in a dictionary of key-value pairs and updates the session state accordingly
def callbackUpdater(key_value_dict: dict):
    print(key_value_dict)
    for key, value in key_value_dict.items():
        st.session_state[key] = value

# This function takes in username and password strings, checks if they exist, and then authenticates the 
# input username and password
def UserLogin(username, password):
    if not username:
        return "Please enter a username", 0
    if not password:
        return "Please enter a password", 0
    
    account = UsersDB.find_one({"username": username})
    if not account:
        return "Username not found", 0
    
    if bcrypt.checkpw(password.encode('utf-8'), account["password"]):
        st.session_state.loggedIn = True
        st.session_state.Username = username
        if account["admin"] == True:
            st.session_state.admin = True
        return "Log in successfull!", account["_id"]
    else:
        return "Password is invalid", 0
        
# This function takes in username, password, and confirmpassword strings, verifies several axoms that usernames and passwords
# must follow, and if found valid the account is created
def registerUser(username, password, confirmpassword, name, home_address, phone_number, email_address):
    if not username:
        return "Please enter a username", 0
    if not password:
        return "Please enter a password", 0
    if password != confirmpassword:
        return "Passwords must match", 0
    if not name:
        return "Please enter a name", 0
    if not home_address:
        return "Please enter a home address", 0
    if not phone_number:
        return "Please enter a phone number", 0
    if not email_address:
        return "Please enter an email address", 0
        
    if UsersDB.count_documents({"username":username}) > 0:
        return "Username taken", 0
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    UsersDB.insert_one({"username": username, "password": hashed_password, "admin": False, "name": name, "home_address": home_address, "phone_number": phone_number, "email_address": email_address})
    st.session_state.registering = False
    st.session_state.loggedIn = True
    st.session_state.Username = username
    return "Registration successfull!", 1


# Here is a callback function that clears the data or inserts random data

def mongoDBhandler(collections, call_type="None"):
    collection_list = ["users", "tickets", "drawings", "admin", "winners"]
    for collection in collections:
        if collection in collection_list:
            if call_type == "Delete":
                LottoDB[collection].delete_many({})
            

# Here is a callback function that is used when redeeming tickets online to update 
# state to show the redeeming portal and also pass in the necessary ticket data
def sendToRedeeming(ticket):
    st.session_state.redeemingTicket = ticket
                        


#---------------------------------------------------------#
#------- Here marks where front-end begins (kinda) -------#
#---------------------------------------------------------#

# Page title
st.title("Texas Lottery Companion App")

for key, value in st.session_state.items():
    #st.write(key, value)
    pass

# Within this if block is any page after login is achieved
if st.session_state.loggedIn == True:

    # Make all of the sidebar functionality here
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.Username}! {'(admin)' if st.session_state.admin else ''}")

        st.button("Logout", on_click=callbackUpdater, args=[{"Username":None, "loggedIn":False, "admin":False}])

        if st.session_state.admin == True:
            checked = st.toggle("Delete data?")
            if checked:
                if st.button("CLEAR DATA", on_click=mongoDBhandler, args=[["tickets", "drawings", "winners"], "Delete"]):
                    st.write("Data cleared!")

    # This if block is specifically for the admin page
    if st.session_state.admin == True:
        drawingsTab, systemTab, manageTicketTab = st.tabs(["Make drawing", "View System Status", "Create/Delete/Change Ticket"])

        with drawingsTab:
            ticket_list = []
            for ticket in AdminDB.find():
                ticket_list.append(f"{ticket['ticket_type']} - ${ticket['ticket_price']}0")
            ticket_type = st.selectbox("Ticket Type:", ticket_list, index=None, placeholder="")
            if ticket_type:
                ticket_type = ticket_type.split(' - ')[0]
                with st.form("ticket"):
                    st.write("Enter drawn numbers here:")
                    numberColumns = st.columns(5)
                    number1 = numberColumns[0].number_input("Number 1", 1, 50, None, key="0num")
                    number2 = numberColumns[1].number_input("Number 2", 1, 50, None, key="1num")
                    number3 = numberColumns[2].number_input("Number 3", 1, 50, None, key="2num")
                    number4 = numberColumns[3].number_input("Number 4", 1, 50, None, key="3num")
                    number5 = numberColumns[4].number_input("Number 5", 1, 50, None, key="4num")
                    ticketNumbers = [number1, number2, number3, number4, number5]
                    good = True
                    if st.form_submit_button("Submit Ticket"):
                        for i in range(5):
                            if not st.session_state[f"{i}num"]:
                                good = False
                        if good:
                            DrawingsDB.insert_one({"username": st.session_state.Username, "ticket_numbers": ticketNumbers, "ticket_type": ticket_type, "date": datetime.today()})
                            st.write("Drawing submitted!")
                            winner_winner_tickets = list(TicketsDB.find({"ticket_type" : ticket_type, "ticket_status" : "Not Yet Drawn"}))
                            payouts = {}
                            for ticket in winner_winner_tickets:
                                winner = ticket["username"]
                                payout = float(ticket["payout"])
                                matching_nums = [entry for entry in ticketNumbers if entry in ticket["ticket_numbers"]]
                                percentages_list = [0, 0.01, 0.05, 0.20, 1]
                                if len(matching_nums):
                                    payout *= percentages_list[len(matching_nums) - 1]
                                else:
                                    payout = 0
                                num_string = ''
                                for num in ticketNumbers:
                                    num_string += str(num) + ' '
                                if payout and ticket["ticket_status"] == "Not Yet Drawn":
                                    TicketsDB.update_one({"_id": ticket["_id"]}, {"$set": {"ticket_status": f"You won! Your winnings are: ${payout}. Drawing made on {datetime.today()} with the following numbers: {num_string}"}})
                                    payout_dict = {"username": winner, "ticket_id": ticket["_id"], "payout": payout, "paid": False, "original_nums": ticket["ticket_numbers"], "drawing_nums": ticketNumbers, "matching_nums": matching_nums, "date": datetime.today()}
                                    WinnersDB.insert_one(payout_dict)
                                    payouts[winner] = payout_dict
                                else:
                                    TicketsDB.update_one({"_id": ticket["_id"]}, {"$set": {"ticket_status": f"No match. Better luck next time! Drawing made on {datetime.today()} with the following numbers: {num_string}"}})
                                    
                        else:
                            st.write("Please enter a number for each entry!")
                            good = True

        with systemTab:
            st.write("You are viewing system status.")
            time_period = st.select_slider("Select time period to view", options=["7 days", "30 days", "180 days", "365 days", "All Time"])
            if "days" not in time_period:
                winners = WinnersDB.find()
                purchased_tickets = TicketsDB.find()
            else:
                dTime = int(time_period.split(" ")[0])
                winners = WinnersDB.find({"date" : {"$gte": datetime.now() - timedelta(days=dTime)}, "paid" : True})
                purchased_tickets = TicketsDB.find({"date" : {"$gte": datetime.now() - timedelta(days=dTime)}})
                pendings = WinnersDB.find({"date" : {"$gte": datetime.now() - timedelta(days=dTime)}, "paid" : False})
            
            payoutsTab, revenueTab, pendingTab = st.tabs(["View Paid Out Winning Ticket", "View Purchased Ticket Revenue", "View Un-Paid Winning Tickets"])
            with payoutsTab:
                totalPayouts = 0
                displayinfocols = st.columns(3)
                for winner in winners:
                    displayinfocols[0].write(winner["username"])
                    displayinfocols[1].write(winner["payout"])
                    displayinfocols[2].write(winner["date"])
                    totalPayouts += winner["payout"]
                st.write(f"Total paid payouts in the selected period: ${totalPayouts}")
            
            with revenueTab:
                totalRevenue = 0
                displayinfocols = st.columns(3)
                for ticket in purchased_tickets:
                    displayinfocols[0].write(ticket["username"])
                    displayinfocols[1].write(ticket["price"])
                    displayinfocols[2].write(ticket["date"])
                    totalRevenue += ticket["price"]
                st.write(f"Total revenue in the selected period: ${totalRevenue}")

            with pendingTab:
                totalPendings = 0
                displayinfocols = st.columns(3)
                for pender in pendings:
                    displayinfocols[0].write(pender["username"])
                    displayinfocols[1].write(pender["payout"])
                    displayinfocols[2].write(pender["date"])
                    totalPendings += pender["payout"]
                st.write(f"Total pending payouts in the selected period: ${totalPendings}")
                
        
        with manageTicketTab:
            with st.form("Create new ticket"):
                new_type = st.text_input("New Ticket Name")
                new_price = st.number_input("New Ticket Price")
                new_payout = st.number_input("New Ticket Payout")
                if st.form_submit_button("Submit"):
                    AdminDB.insert_one({"ticket_type": new_type, "ticket_price": new_price, "ticket_payout": new_payout})
                    st.write("Ticket submitted!")
                    
            with st.form("Delete ticket"):
                ticket_list = []
                for ticket in AdminDB.find():
                    ticket_list.append(f"{ticket['ticket_type']} - ${ticket['ticket_price']}0")
                delete_type = st.selectbox("Browse/Search Ticket to delete:", ticket_list, index=None, placeholder="")
                if st.form_submit_button("Submit") and delete_type:
                    AdminDB.delete_one({"ticket_type": delete_type.split(" - ")[0]})
                    st.write("Ticket deleted!")
    
    # This else block is specifically for the user page
    else:
        purchaseTab, inventoryTab, previousNumbersTab, profileTab = st.tabs(["Browse", "Inventory", "View Previous Winning Numbers", "View Profile"])

        with inventoryTab:
            # Check to see if the user is redeeming a ticket or not
            if st.session_state.redeemingTicket:
                # If there is a ticket currently being redeemed, then handle it.
                st.write("Winning ticket info:")
                winning_ticket_cols = st.columns(3)
                winning_ticket_cols[0].write("ticket type")
                winning_ticket_cols[0].write(st.session_state.redeemingTicket["ticket_type"])
                winning_ticket_cols[1].write("ticket id")
                winning_ticket_cols[1].write(st.session_state.redeemingTicket["_id"])
                winning_ticket_cols[2].write('payout')
                winning_ticket_cols[2].write(f"{st.session_state.redeemingTicket['payout']}0")
                with st.form(f"Claim winnnings of {st.session_state.redeemingTicket['payout']}0 online"):
                    
                    credit_debitTab, paypalTab = st.tabs(["Deposit to bank", "Deposit to Paypal"])
                    with credit_debitTab:
                        st.write("Credit/Debit")
                        ccnumCols = st.columns(4)
                        credit_debit_number1 = ccnumCols[0].text_input("ccnums1", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        credit_debit_number2 = ccnumCols[1].text_input("ccnums2", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        credit_debit_number3 = ccnumCols[2].text_input("ccnums3", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        credit_debit_number4 = ccnumCols[3].text_input("ccnums4", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        ccinfoCols = st.columns([.5, .25, .25])
                        credit_debit_exp = ccinfoCols[0].text_input("Expiration Date", placeholder="MM/YY", max_chars=5)
                        credit_debit_cvv = ccinfoCols[1].text_input("CVV", placeholder="XXX", max_chars=3)
                        credit_debit_zip = ccinfoCols[2].text_input("Zip Code", placeholder="XXXXX", max_chars=5)
                    
                    with paypalTab:
                        paypal_email = st.text_input("Paypal Email")
                        paypal_password = st.text_input("Paypal Password", type="password")

                    goodCC = False
                    goodPP = False
                    chose_bank = False
                    if st.form_submit_button(f"Claim ${st.session_state.redeemingTicket['payout']}0 now!"):
                        if len(credit_debit_number1) == 4 and len(credit_debit_number2) == 4 and len(credit_debit_number3) == 4 and len(credit_debit_number4) == 4 and len(credit_debit_exp) == 5 and len(credit_debit_cvv) == 3 and len(credit_debit_zip) == 5:
                            goodCC = True
                            chose_bank = True
                        
                        if "@" in paypal_email and "." in paypal_email and len(paypal_password) > 0:
                            goodPP = True
                            chose_bank = False
                            goodCC = False

                        if goodCC or goodPP:
                            good = True

                        if goodCC:
                            TicketsDB.update_one({"_id": st.session_state.redeemingTicket["_id"]}, {"$set": {"ticket_status": f"You won and claimed ${st.session_state.redeemingTicket['payout']}0 To bank using card XXXX-XXXX-XXXX-{credit_debit_number4} on {datetime.today()}."}})
                            WinnersDB.update_one({"ticket_id": st.session_state.redeemingTicket["_id"]}, {"$set": {"paid": True}})
                            st.write("Winnings claimed! Please allow up to 72 hours for your bank to receive your winnings.")
                            st.session_state.redeemingTicket = None
                            st.rerun()
                        elif goodPP:
                            TicketsDB.update_one({"_id": st.session_state.redeemingTicket["_id"]}, {"$set": {"ticket_status": f"You won and claimed ${st.session_state.redeemingTicket['payout']}0 To paypal belonging to {paypal_email} on {datetime.today()}."}})
                            WinnersDB.update_one({"ticket_id": st.session_state.redeemingTicket["_id"]}, {"$set": {"paid": True}})
                            st.write("Winnings claimed! Please allow up to 72 hours for PayPal to receive your winnings.")
                            st.session_state.redeemingTicket = None
                            st.rerun()
                        else:
                            st.write("Please enter all valid info!")
                            good = True
                go_back_button = st.button("Cancel redemtion", on_click=lambda: setattr(st.session_state, 'redeemingTicket', None))
            else:
                # This means that the user is in the inventory tab but not redeeming a ticket
                myTickets = list(TicketsDB.find({"username": st.session_state.Username}))
                if st.button("Refresh") and st.session_state.refreshReady:
                    st.session_state.refreshReady = False
                    st.rerun()
                if st.session_state.refreshReady == False:
                    st.session_state.refreshReady = True
                if len(myTickets) == 0:
                    st.write("You have no tickets!")
                else:
                    ticketColumns = []
                    ticket_containers = []
                    for ticket in myTickets:
                        ticket_containers.append(st.container())
                        with ticket_containers[-1]:
                            ticketColumns.append(st.columns(5))
                            with ticketColumns[-1][0]:
                                st.write("Ticket Type: ")
                                st.write(ticket["ticket_type"])
                            with ticketColumns[-1][1]:
                                st.write("Ticket ID: ")
                                st.write(ticket["_id"])
                            with ticketColumns[-1][2]:
                                st.write("Ticket Numbers: ")
                                nums = [str(i) for i in ticket["ticket_numbers"]]
                                st.write(", ".join(nums))
                            with ticketColumns[-1][3]:
                                st.write("Ticket Status: ")
                                st.write(ticket["ticket_status"])
                            if "winnings" in ticket["ticket_status"]:
                                if ticket["payout"] > 599: 
                                    with ticketColumns[-1][4]:
                                        st.write(f"To claim winnings of over $599, please bring your ticket id to your nearest TLC office. Your ticket id is {ticket['_id']}")
                                else:
                                    with ticketColumns[-1][4]:
                                        go_to_redeem = st.button(f"Redeem ${ticket['payout']}0 online!", on_click=sendToRedeeming, args=[ticket])
                
        with purchaseTab:
            ticket_list = []
            for ticket in AdminDB.find():
                ticket_list.append(f"{ticket['ticket_type']} - ${ticket['ticket_price']}0 - Max prize: ${ticket['ticket_payout']}0")
            ticket_type = st.selectbox("Browse/Search Available Tickets:", ticket_list, index=None, placeholder="")
            if ticket_type:
                with st.form("ticket"):
                    st.write("Please enter your ticket numbers below.")
                    numberColumns = st.columns(5)
                    number1 = numberColumns[0].number_input("Number 1", 1, 50, None, key="0num")
                    number2 = numberColumns[1].number_input("Number 2", 1, 50, None, key="1num")
                    number3 = numberColumns[2].number_input("Number 3", 1, 50, None, key="2num")
                    number4 = numberColumns[3].number_input("Number 4", 1, 50, None, key="3num")
                    number5 = numberColumns[4].number_input("Number 5", 1, 50, None, key="4num")
                    ticketNumbers = [number1, number2, number3, number4, number5]
                    good = False
                    credit_debitTab, paypalTab = st.tabs(["Pay with Credit/Debit", "Pay with Paypal"])

                    with credit_debitTab:
                        st.write("Credit/Debit")
                        ccnumCols = st.columns(4)
                        credit_debit_number1 = ccnumCols[0].text_input("ccnums1", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        credit_debit_number2 = ccnumCols[1].text_input("ccnums2", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        credit_debit_number3 = ccnumCols[2].text_input("ccnums3", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        credit_debit_number4 = ccnumCols[3].text_input("ccnums4", max_chars=4, placeholder="XXXX",label_visibility="collapsed")
                        ccinfoCols = st.columns([.5, .25, .25])
                        credit_debit_exp = ccinfoCols[0].text_input("Expiration Date", placeholder="MM/YY", max_chars=5)
                        credit_debit_cvv = ccinfoCols[1].text_input("CVV", placeholder="XXX", max_chars=3)
                        credit_debit_zip = ccinfoCols[2].text_input("Zip Code", placeholder="XXXXX", max_chars=5)
                    
                    with paypalTab:
                        paypal_email = st.text_input("Paypal Email")
                        paypal_password = st.text_input("Paypal Password", type="password")

                    goodCC = False
                    goodPP = False
                    if st.form_submit_button("Submit Ticket"):
                        if len(credit_debit_number1) == 4 and len(credit_debit_number2) == 4 and len(credit_debit_number3) == 4 and len(credit_debit_number4) == 4 and len(credit_debit_exp) == 5 and len(credit_debit_cvv) == 3 and len(credit_debit_zip) == 5:
                            goodCC = True
                        
                        if "@" in paypal_email and len(paypal_password) > 0:
                            goodPP = True

                        if goodCC or goodPP:
                            good = True

                        for i in range(5):
                            if not st.session_state[f"{i}num"]:
                                good = False

                        if good:
                            TicketsDB.insert_one({"username": st.session_state.Username, "ticket_numbers": ticketNumbers, "ticket_type": ticket_type.split(" - ")[0], "price": float(ticket_type.split(" - ")[1][1:-1]), "payout": float(ticket_type.split(": $")[1][:-3]),"ticket_status": "Not Yet Drawn", "date": datetime.now()})
                            st.write("Ticket submitted!")
                        else:
                            st.write("Please enter all valid info!")
                            good = True
        
        with previousNumbersTab:
            prevNumColumns = st.columns(3)
            prevNumColumns[0].write("Ticket Type")
            prevNumColumns[1].write("Ticket Numbers")
            prevNumColumns[2].write("Date")
            for drawing in DrawingsDB.find():
                prevNumColumns[0].write(drawing["ticket_type"])
                prevNumColumns[0].divider()
                numbers_string = ""
                for num in drawing["ticket_numbers"][:-1]:
                    numbers_string += str(num) + ", "
                numbers_string += str(drawing["ticket_numbers"][-1])
                prevNumColumns[1].write(numbers_string)
                prevNumColumns[1].divider()
                prevNumColumns[2].write(drawing["date"])
                prevNumColumns[2].divider()

        with profileTab:
            if st.toggle("Edit Profile"):
                with st.form("editProfile"):
                    name = st.text_input("Name", value=UsersDB.find_one({"username": st.session_state.Username})["name"])
                    hAddr = st.text_input("Home Address", value=UsersDB.find_one({"username": st.session_state.Username})["home_address"])
                    phNum = st.text_input("Phone Number", value=UsersDB.find_one({"username": st.session_state.Username})["phone_number"])
                    emailAddr = st.text_input("Email Address", value=UsersDB.find_one({"username": st.session_state.Username})["email_address"])
                    if st.form_submit_button("Submit"):
                        UsersDB.update_one({"username": st.session_state.Username}, {"$set": {"name": name, "home_address": hAddr, "phone_number": phNum, "email_address": emailAddr}})
                        st.write("Profile updated!")
            else:
                st.write("Username: ", st.session_state.Username)
                st.write("Account ID: ", UsersDB.find_one({"username": st.session_state.Username})["_id"])
                st.write("Account Status: ", "Active")
                st.write(f"Account Type: ", 'user' if st.session_state.admin == False else 'admin')
                st.write("Name: ", UsersDB.find_one({"username": st.session_state.Username})["name"])
                st.write("Home Address: ", UsersDB.find_one({"username": st.session_state.Username})["home_address"])
                st.write("Phone Number: ", UsersDB.find_one({"username": st.session_state.Username})["phone_number"])
                st.write("Email Address: ", UsersDB.find_one({"username": st.session_state.Username})["email_address"])


# Within this else block is any page before login is achieved
else:

    # Within this if block is any page during registration
    if st.session_state.registering:
        with st.form("register"):
            st.write("Please enter your desired username and password below to create an account.")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirmpassword = st.text_input("Confirm Password", type="password")
            name = st.text_input("Name")
            home_address = st.text_input("Home Address")
            phone_number = st.text_input("Phone Number")
            email_address = st.text_input("Email Address")
            if st.form_submit_button("Register"):
                message, success = registerUser(username, password, confirmpassword, name, home_address, phone_number, email_address)
                st.error(message)
                if success:
                    st.rerun()
        st.button("Go to login", on_click=callbackUpdater, args=[{"registering": False}])
        
    # Within this else block is any page before we are logged in while not registering
    else:
        with st.form("login"):
            st.write("Please log in below.")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                message, success = UserLogin(username, password)
                st.error(message)
                if success:
                    st.rerun()
        st.button("Go to register", on_click=callbackUpdater, args=[{"registering": True}])
