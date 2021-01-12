from TDAgent import *
from DQN.DQNAgent import *
from GradientPolicyMethods.REINFORCEAgent import *
from GradientPolicyMethods.REINFORCEAgentWithBaseline import *
from GradientPolicyMethods.ActorCriticAgent import *
import gym
import matplotlib.pyplot as plt
import json

import sys
sys.path.append('../')
import lonesome_town.GodotEnvironment as godot


def reward_func(env, x, x_dot, theta, theta_dot):  # TODO: do something about it
    """
    For cartpole
    :param env:
    :param x:
    :param x_dot:
    :param theta:
    :param theta_dot:
    :return:
    """
    r1 = (env.x_threshold - abs(x)) / env.x_threshold - 0.5
    r2 = (env.theta_threshold_radians - abs(theta)) / env.theta_threshold_radians - 0.5
    reward = r1 + r2
    return reward


class Session:
    def __init__(self, params={}):
        self.agents = None
        self.agents_names = None
        self.environment_type = None
        self.environment_name = None
        self.environment = None
        self.num_episodes = None
        self.show = None
        self.show_every = None
        self.plot = None
        self.return_results = None

        self.session_type = None

        self.set_params_from_dict(params=params)

        self.set_env_and_agent(params)


    # ====== Initialization functions =======================================================


    def set_params_from_dict(self, params={}):
        self.num_episodes = params.get("num_episodes", 100)
        self.show = params.get("show", False)
        self.show_every = params.get("show_every", 10)
        self.environment_type = params.get("environment_type", "gym")
        self.environment_name = params.get("environment_name", "MountainCar-v0")
        self.plot = params.get("plot", False)
        self.return_results = params.get("return_results", False)
        self.session_type = params.get("session_type", "REINFORCE")

    def set_env_and_agent(self, params):
        if self.environment_type == "gym":
            self.environment = gym.make(self.environment_name)
        elif self.environment_type == "godot":
            self.environment = godot.GodotEnvironment(params["environment_info"])
        if self.session_type == "tile coder":  # TODO: might be a problem later
            params["agent_info"]["function_approximator_info"]["env_min_values"] = self.environment.observation_space.low
            params["agent_info"]["function_approximator_info"]["env_max_values"] = self.environment.observation_space.high
        self.agents_names = self.environment.agent_names
        self.initialize_agents(params["agent_info"])
        #self.initialize_agent(params["agent_info"])

    def initialize_agents(self, params={}):
        self.agents = {}
        for agent_name in self.agents_names:
            self.agents[agent_name] = self.create_agent(params)

    def create_agent(self, params={}):
        agent = None
        if self.session_type == "DQN test":
            agent = DQNAgent(params)
        elif self.session_type == "tile coder test":
            agent = TDAgent(params)
        elif self.session_type == "REINFORCE":
            agent = REINFORCEAgent(params)
        elif self.session_type == "REINFORCE with baseline":
            agent = REINFORCEAgentWithBaseline(params)
        elif self.session_type == "actor-critic":
            agent = ActorCriticAgent(params)
        else:
            print("agent not initialized")
        return agent

    def initialize_agent(self, params={}):
        if self.session_type == "DQN test":
            self.agent = DQNAgent(params)
        elif self.session_type == "tile coder test":
            self.agent = TDAgent(params)
        elif self.session_type == "REINFORCE":
            self.agent = REINFORCEAgent(params)
        elif self.session_type == "REINFORCE with baseline":
            self.agent = REINFORCEAgentWithBaseline(params)
        elif self.session_type == "actor-critic":
            self.agent = ActorCriticAgent(params)
        else:
            print("agent not initialized")

    # ====== Execution functions =======================================================
    def get_action_data(self, agents_data, start=False):
        action_data = []
        for agent_data in agents_data:
            agent_name = agent_data["name"]
            #agent_state
            if start is True:
                action = self.agents[agent_name].start(agent_data["state"])
            else:
                action = self.agents[agent_name].step(agent_data["state"], agent_data["reward"])
            action_data.append({"name": agent_name, "action": action})
        return action_data

    def episode(self, episode_id):
        # reset environment
        if self.environment_type == "godot":
            render = False
            if (self.show is True) and (episode_id % self.show_every == 0):
                render = True
            environment_data = self.environment.reset(render)
        else:
            environment_data = self.environment.reset()
        action_data = self.get_action_data(environment_data, start=True)
        #action = self.agent.start(agent_data)
        episode_reward = 0
        done = False
        success = False

        if (self.show is True) and (episode_id % self.show_every == 0):
            print(f'EPISODE: {episode_id}')

        while not done:
            # take action in the environment
            agents_data, done, n_frames = self.environment.step(action_data) # self.environment.step([float(action)]) | if continuous mountian car
            # shape the reward and add it to the episode reward
            if self.environment_name == "CartPole-v0":  # TODO : might want to change that
                x, x_dot, theta, theta_dot = new_state
                #reward = reward_func(self.environment, x, x_dot, theta, theta_dot)
                # TODO : change that
            episode_reward += agents_data[0]["reward"] # reward
            # render environment
            if (self.show is True) and (episode_id % self.show_every == 0) and (self.environment_type != "godot"):
                    self.environment.render()

            if not done:
                action_data = self.get_action_data(agents_data)
                #action = self.agent.step(new_state, reward)
            else:
                # success conditions for mountain car problem
                if self.environment_name == "MountainCar-v0":  # TODO : might want to change that too
                    if new_state[0] >= self.environment.goal_position:
                        success = True
                        reward = 1

                # end step for all the agents
                for agent_data in agents_data:
                    agent_name = agent_data["name"]
                    self.agents[agent_name].end(agent_data["state"], agent_data["reward"])
                #self.agent.end(new_state, reward)

                if self.session_type == "REINFORCE" or self.session_type == "REINFORCE with baseline":
                    self.agent.learn_from_experience()

                return episode_reward, success

    def average_rewards(self, rewards):
        avg_rewards = []
        # transform the rewards to their avergage on the last n episodes (n being specified in the class parameters)
        for i in range(len(rewards)):  # iterate through rewards
            curr_reward = rewards[i]
            last_n_rewards = [rewards[j] for j in range(i - 100 - 1, i) if j >= 0]
            last_n_rewards.append(curr_reward)
            avg_reward = np.average(last_n_rewards)
            avg_rewards += [avg_reward]

        return avg_rewards

    def run(self):
        episode_reward = 0
        success = False
        rewards = np.array([])
        for id_episode in range(self.num_episodes):
            episode_reward, success = self.episode(id_episode)
            print(id_episode)
            print(episode_reward)
            print(success)
            rewards = np.append(rewards, episode_reward)
        if self.plot is True:
            plt.plot(self.average_rewards(rewards))
            plt.show()
            #print(episode_reward)

        if self.return_results:
            return rewards



if __name__ == "__main__":
    # '../LonesomeTown/params/first_test_params.json'
    with open('params/experiments/DQN_params.json') as json_file:
        data = json.load(json_file)
        session_parameters = data["session_info"]
        session_parameters["agent_info"] = data["agent_info"]
        session_parameters["environment_info"] = data["environment_info"]

    sess = Session(session_parameters)
    sess.run()
