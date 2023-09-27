from mesa import Model,Agent
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import numpy as np
import random
import copy
from operator import attrgetter

#Model Parameters (to be used in jupyter notebook)
#zebra_configuration = []
#starting_breed_fee = 0.5

class Customer(Agent):
    # Represents a zebpay customer or potential zebpay customer

    def __init__(self, unique_id, model, cust_id):
        #super().__init__(self.model)
        self.unique_id = unique_id
        self.cust_id = cust_id
        self.agent_type = "customer" # sets the agent type to customer
        self.zebaffinity = 0 # an indicator of affinity to zebpay? something that needs to be discussed
        self.cryptoaffinity = 0 # an indicator of affinity to crypto, i.e. preference to buy
        self.zeb_tokens = [] # list of owned tokens
        self.breeding_fees_paid = 0

    def own_token(self,token):
        self.zeb_tokens.append(token) # adds a token to the list of owned tokens
        token.owners.append(self) # adds an owner to the tokens list of owners

    #def step(self):

class ZebToken(Agent):
    # Tokens that Zebpay issues to customers

    def __init__(self, unique_id, model, category, schedule, cat_index):

        #super().__init__(self.model)
        self.unique_id = unique_id
        self.mates = 0
        self.category = category
        self.cat_index = cat_index
        self.owners = [] #all who have ever owned this token; last one is current owner
        self.agent_type = "token"
        self.parents = []
        self.breed_cost_multiplier = 1
        self.schedule = schedule
        self.decision = 0 # which decision led to the creation of this token

    #def step(self):


class ZebraNFTModel(Model):
    def __init__(self, customer_num, token_num, dist_params, token_cat, category_weights, est_mating_cutoff, breeding_choice_type, transfer_details, mates_per_step, distribution_option):

        self.customer_num = customer_num # number of customers in model
        self.token_num = token_num # number of tokens being distributed
        self.schedule = RandomActivation(self) # reandom creation of agents
        self.zeb_token_list = [] # list of tokens
        self.customer_list = [] # list of customers
        self.dist_params = dist_params
        self.latest_unique_id = 0
        self.latest_cust_id = 0
        self.category_weights = category_weights
        self.dist_params = dist_params
        self.datacollector = DataCollector()
        self.owner_list = []
        self.token_cat = token_cat # categories of current token
        self.breed_cost_cutoff = est_mating_cutoff # estimated cutoff for mating a token
        self.breeding_choice_type = breeding_choice_type
        self.transfer_type = transfer_details[0] # type of token transfer that occurs between customers at each step
        self.number_of_transfers = transfer_details[1]
        self.mates_per_step = mates_per_step # number of mates per step
        self.distribution_option = distribution_option # choice of how to select mating pairs

        #generate customer agents
        for i in range(customer_num): #runs for as many customers that need to be created
            customer_agent = Customer(self.latest_unique_id, self, self.latest_cust_id) # create a new customer agent
            self.schedule.add(customer_agent) # adds a customer to the schedule
            self.customer_list.append(customer_agent) # adds a customer to the list of customers
            self.latest_unique_id += 1
            self.latest_cust_id +=1

        #generate token agents
        for cat_index, category in enumerate(token_cat):
            for j in range(round(token_num*self.category_weights[category])): # runs for as many tokens that need to be created
                token_agent = ZebToken(self.latest_unique_id, self, category, self.schedule, cat_index) # creates a token agent
                self.schedule.add(token_agent) # adds the token agent to the schedule
                self.zeb_token_list.append(token_agent) # adds the token agent to the token list
                owner = self.random.choice(self.customer_list) # selects a customer at random from the list
                owner.own_token(token_agent) # assigns this token to the randomly selected customer from the list
                if owner not in self.owner_list:
                    self.owner_list.append(owner) #adds the owner to the list of token owners if not already in there
                self.latest_unique_id += 1

        self.running = True


    def breeding_choice(self, partner_token_list, initiating_token_list, breeding_choice_type):
        # minimize cost
        if breeding_choice_type == 0:
            initiating_token = min(initiating_token_list, key=attrgetter('breed_cost_multiplier'))
            #print(partner_token_list)
            partner_token = min(partner_token_list, key=attrgetter('breed_cost_multiplier'))
        # maximize category
        elif breeding_choice_type == 1:
            initiating_token = max(initiating_token_list, key=attrgetter('cat_index'))
            partner_token = max(partner_token_list, key=attrgetter('cat_index'))
        # randomly picks between maximizing category and minimizing cost, should result in 50% of each
        elif breeding_choice_type == 2:
            dice_roll = random.choice([1,2])
            if dice_roll ==1:
                initiating_token = min(initiating_token_list, key=attrgetter('breed_cost_multiplier'))
                partner_token = min(partner_token_list, key=attrgetter('breed_cost_multiplier'))
            elif dice_roll ==2:
                initiating_token = max(initiating_token_list, key=attrgetter('cat_index'))
                partner_token = max(partner_token_list, key=attrgetter('cat_index'))
        return [initiating_token, partner_token]


    def transfer_choice(self, transfer_type, number_of_transfers):
        # random token transfers per step
        if transfer_type == 1:
            owner_list = copy.copy(self.owner_list)[:min(number_of_transfers,len(self.owner_list))]
            recipient_list = random.sample(self.customer_list, len(owner_list))

        return [owner_list, recipient_list]

    def mating_distribution(self, distribution_option, parameters, mates_per_step):
        initiator_list = copy.copy(self.owner_list) # recreates the customer list for this step
        partner_list = copy.copy(self.owner_list) 
             
        if distribution_option == 0: # creates random mating lists
            new_partner_list = random.shuffle(partner_list)
            new_initiator_list = random.shuffle(initiator_list)
        elif distribution_option == 1: # creates a mating list with the majority as high value tokens
            initiator_list = sorted(initiator_list, key = attrgetter('cat_index'), reverse= True) # sorts in descending order
            new_initiator_list = initiator_list[0:round(self.mates_per_step*self.customer_num)]
            new_partner_list = random.shuffle(partner_list)
        elif distribution_option == 2: # This option creates mating lists based on the lognormal distribution 
            initiator_list = sorted(initiator_list, key = attrgetter('cat_index'), reverse= True) # sorts in descending order
            distr= np.random.lognormal(0.1,0.25,round(self.mates_per_step*self.customer_num))
            initiator_indices_list = distr/max(distr)*self.customer_num # creates an adjusted list of indices based on the distribution
            new_initiator_list = []
            for i in initiator_indices_list.astype('int'):
                new_initiator_list.append(initiator_list[i])
            new_partner_list = random.sample(partner_list, len(new_initiator_list))

        return [new_initiator_list, new_partner_list]

    def mate(self, initiator, partner, breeding_choice_type):
        dice_roll = random.choice(range(100))
        #Customers select tokens to mate
        initiator_token_list = initiator.zeb_tokens
        #print(str(initiating_token.breed_cost_multiplier) + " " + str(min(token.breed_cost_multiplier for token in initiators_tokens)))
        partner_token_list = partner.zeb_tokens
        [initiating_token, partner_token] = self.breeding_choice(partner_token_list, initiator_token_list, breeding_choice_type) # select type of breeding choice

        if (initiating_token.breed_cost_multiplier < self.breed_cost_cutoff) & (partner_token.breed_cost_multiplier < self.breed_cost_cutoff):
            if (partner_token not in initiating_token.parents) or (partner_token.parents not in initiating_token.parents): # check to make sure they are not related

                new_token_category = "none"
                if dice_roll <= 2 :
                    new_token_category = self.token_cat[-1]
                    decision = 1
                    #print("9 percent rare = "+ new_token_category)
                elif (dice_roll >2) & (dice_roll<=49):
                    new_token_category = initiating_token.category
                    decision = 2
                    #print("initiating category" + new_token_category)
                elif (dice_roll >49) & (dice_roll<=89):
                    new_token_category = partner_token.category
                    decision = 3
                    #print("partner category = " + new_token_category)

                elif (dice_roll >89) & (dice_roll<=100):
                    init = self.token_cat.index(initiating_token.category)
                    partn = self.token_cat.index(partner_token.category)
                    new_token_category = self.token_cat[min(abs(min(init,partn)-2), 0)] # selects the category less than both parents or the lowest 
                    decision = 4
                    #print("lowest of parente = "+new_token_category)
                cat_index = self.token_cat.index(new_token_category)
                new_token = ZebToken(self.latest_unique_id, self, new_token_category, self.schedule, cat_index) # creates a new token
                new_token.owners.append(initiator) #add owner to token owners list
                new_token.parents.append([initiator,partner]) # add parents to parents list
                new_token.decision = decision
                initiator.zeb_tokens.append(new_token) #adds the new token to the initiator
                initiating_token.breed_cost_multiplier = initiating_token.breed_cost_multiplier * 2 #change the breed cost
                partner_token.breed_cost_multiplier = partner_token.breed_cost_multiplier * 2 #change the breed cost


                self.latest_unique_id+=1
                self.schedule.add(new_token)
                self.zeb_token_list.append(new_token)

    def step(self):
        initiator_list = copy.copy(self.owner_list) # recreates the customer list for this step
        partner_list = copy.copy(self.owner_list) #creates a shuffled list to mate with 
        random.shuffle(partner_list)
        # mating
        for partner_id, initiator in enumerate(initiator_list):
            partner = partner_list[partner_id]
            self.mate(initiator, partner, self.breeding_choice_type)

        # transfers
        [list1, list2] = self.transfer_choice(self.transfer_type, self.number_of_transfers)
        for transfer_index, owner in enumerate(list1):
            if len(owner.zeb_tokens) != 0:
                random_token_index = random.choice(range(len(owner.zeb_tokens)))
                token_to_transfer = owner.zeb_tokens[random_token_index] #randomly pick an owners tokens and assign to new owner
                #print(owner.zeb_tokens.pop(random_token_index))
                if len(owner.zeb_tokens)==0: #removes the customer from the owner list if they don't own any tokens
                    self.owner_list.remove(owner)
                list2[transfer_index].zeb_tokens.append(token_to_transfer)
                #print(list2[transfer_index])
                if list2[transfer_index] not in self.owner_list:
                    self.owner_list.append(list2[transfer_index]) #adds the person recieving the token to the owner list 






            
            
