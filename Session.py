from TDAgent import *
from DQN.DQNAgent import *
from GradientPolicyMethods.REINFORCEAgent import *
from GradientPolicyMethods.REINFORCEAgentWithBaseline import *
from GradientPolicyMethods.ActorCriticAgent import *
import gym
import matplotlib.pyplot as plt
import json

import os
import pathlib
import sys

import godot_interface.GodotEnvironment as godot

from utils import *


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
        self.agent = None
        self.environment_type = None
        self.environment_name = None
        self.environment = None

        self.num_episodes = None
        self.session_type = None
        self.is_multiagent = None

        self.show = None
        self.show_every = None

        self.plot = None
        self.return_results = None

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
        self.is_multiagent = params.get("is_multiagent", False)
 
    def set_env_and_agent(self, params):
        env_params = params.get("environment_info", {})
        self.init_env(env_params)
        agent_params = params.get("agent_info", {})
        self.init_agent(agent_params)
    
    def init_env(self, env_params):
        """the environment is set differently if it's a gym environment or a godot environment.

        Args:
            env_params (dict): used only in case of a godot env.
        """
        if self.environment_type == "gym":
            self.environment = gym.make(self.environment_name)
        elif self.environment_type == "godot":
            self.environment = godot.GodotEnvironment(env_params)
    
    def init_agent(self, agent_params):
        """initialize one or several agents

        Args:
            agent_params (dict)
        """
        if self.is_multiagent:
            self.agents_names = self.environment.agent_names
            self.init_multiagent(agent_params)
        else:
            self.agent = self.init_single_agent(agent_params)

    def init_multiagent(self, agent_params):
        self.agent = {}
        for agent_name in self.agents_names:
            self.agent[agent_name] = self.init_single_agent(agent_params)

    def init_single_agent(self, agent_params):
        """Create and return an agent. The type of agent depends on the self.session_type parameter

        Args:
            agent_params (dict)

        Returns:
            Agent: the agent initialized
        """
        agent = None
        if self.session_type == "DQN test":
            agent = DQNAgent(agent_params)
        elif self.session_type == "tile coder test":
            agent = self.init_tc_agent(agent_params)
        elif self.session_type == "REINFORCE":
            agent = REINFORCEAgent(agent_params)
        elif self.session_type == "REINFORCE with baseline":
            agent = REINFORCEAgentWithBaseline(agent_params)
        elif self.session_type == "actor-critic":
            agent = ActorCriticAgent(agent_params)
        else:
            print("agent not initialized")
        return agent
    
    def init_tc_agent(self, agent_params):
        """initialization of a tile coder agent, which depends on the gym environment

        Args:
            agent_params (dict)

        Returns:
            Agent
        """
        assert self.environment_name == "gym", "tile coder not supported for godot environments"
        
        params["agent_info"]["function_approximator_info"]["env_min_values"] = \
            self.environment.observation_space.low
        params["agent_info"]["function_approximator_info"]["env_max_values"] = \
            self.environment.observation_space.high
        agent = TDAgent(agent_params)
         
        return agent

    # ====== Agent execution functions =======================================================

    def get_agent_action(self, state_data, reward_data=None, start=False):
        if self.is_multiagent:
            action_data = self.get_multiagent_action(state_data=state_data,
                                                    reward_data=reward_data,
                                                    start=start)
        else:
            action_data = self.get_single_agent_action(agent=self.agent, 
                                        state_data=state_data, 
                                        reward_data=reward_data, 
                                        start=start)
        return action_data
    
    def get_multiagent_action(self, state_data, reward_data=None, start=False):
        """ distribute states to all agents and get their actions back.

        Args:
            state_data (dict)
            reward_data (dict, optional): Defaults to None.
            start (bool, optional): indicates whether it is the first step of the agent. 
                                    Defaults to False.

        Returns:
            dict
        """
        action_data = []
        # for each agent, get 
        for n_agent in range(len(state_data)):
            agent_name = state_data[n_agent]["name"]
            agent_state = state_data[n_agent]["state"]
            action = self.get_single_agent_action(agent=self.agent[agent_name], 
                                        state_data=agent_state, 
                                        reward_data=reward_data, 
                                        start=start)
            action_data.append({"name": agent_name, "action": action})
        return action_data
    
    def get_single_agent_action(self, agent, state_data, reward_data=None, start=False):
        """if this is the first state of the episode, get the first action of the agent
        else, also give reward of the previous action to complete the previous transition.

        Args:
            agent (Agent)
            state_data (dict)
            reward_data (dict, optional): Defaults to None.
            start (bool, optional): indicates whether it is the first step of the agent. 
                                    Defaults to False.

        Returns:
            int : id of action taken
        """
        if start is True:
            action_data = agent.start(state_data)
        else:
            action_data = agent.step(state_data, reward_data)
        return action_data

    def end_agent(self, state_data, reward_data):
        if self.is_multiagent:
            self.end_multiagent(state_data, reward_data)
        else:
            self.agent.end(state_data, reward_data)
        
    def end_multiagent(state_data, reward_data):
        """send the terminal state and the final reward to every agent so they can 
        complete their last transitions

        Args:
            state_data (dict): [description]
            reward_data (dict): [description]
        """
        for n_agent in range(len(state_data)):
                agent_name = state_data[n_agent]["name"]
                agent_state = state_data[n_agent]["state"]
                agent_reward = reward_data[n_agent]["reward"]

                self.agent[agent_name].end(agent_state, agent_reward)

    # ==== Name to be defined =================================================================

    def episode(self, episode_id):
        """[summary]

        Args:
            episode_id ([type]): [description]

        Returns:
            [type]: [description]
        """
        self.print_episode_count(episode_id=episode_id)
        state_data = self.env_reset()
        action_data = self.get_agent_action(state_data, start=True)

        episode_reward = 0
        done = False
        success = False

        # Main loop
        while not done:
            # run a step in the environment and get the new state, reward and info about whether the 
            # episode is over.
            new_state_data, reward_data, done, _ = self.environment.step(action_data)
             # self.environment.step([float(action)]) | if continuous mountian car
            reward_data = self.shape_reward(state_data, reward_data)
            # save the reward
            episode_reward = self.save_reward(episode_reward, reward_data)
            # render environment (gym environments only)
            self.render_gym_env(episode_id)

            if not done:
                # get the action if it's not the last step
                action_data = self.get_agent_action(new_state_data, reward_data)
            else:
                # get the final reward and success in the mountaincar env
                reward_data, success = self.assess_mc_success(new_state_data)
                self.end_agent(new_state_data, reward_data)
                if self.session_type == "REINFORCE" or self.session_type == "REINFORCE with baseline":
                    self.agent.learn_from_experience()
                return episode_reward, success

    def run(self):
        episode_reward = 0
        success = False
        rewards = np.array([])
        # run the episodes and store the rewards
        for id_episode in range(self.num_episodes):
            episode_reward, success = self.episode(id_episode)
            self.environment.close()
            print(f'EPISODE: {id_episode}')
            print(f'reward: {episode_reward}')
            print(f'success: {success}')
            rewards = np.append(rewards, episode_reward)
        # plot the rewards
        if self.plot is True:
            plt.plot(self.average_rewards(rewards))
            plt.show()
            #print(episode_reward)
        # return the rewards
        
        if self.return_results:
            return rewards

    def godot_env_reset(self):
        """ set the right render type for the godot env episode
        """
        render = False
        if (self.show is True) and (episode_id % self.show_every == 0):
            render = True
        state_data = self.environment.reset(render)
        return state_data

    def env_reset(self):
        """ Reset the environment, in both godot and gym case
        """
        if self.environment_type == "godot":
            state_data = self.godot_env_reset()
        else:
            state_data = self.environment.reset()
        return state_data
    
    def print_episode_count(self, episode_id):
        if ((self.show is True) and (episode_id % self.show_every == 0)):
            print(f'EPISODE: {episode_id}')
    
    def shape_reward(self, state_data, reward_data):
        """ shaping reward for cartpole environment
        """
        if self.environment_name == "CartPole-v0":  # TODO : might want to change that
            x, x_dot, theta, theta_dot = state_data
            reward_data = reward_func(self.environment, x, x_dot, theta, theta_dot)

        return reward_data
    
    def save_reward(self, episode_reward, reward_data):
        """ add the reward to the reward history
        """
        if self.session_type == "godot":
            episode_reward += reward_data[0]["reward"]
        else:
            episode_reward += reward_data
        return episode_reward
    
    def render_gym_env(self, episode_id):
        """ render environment (gym environments only) if specified so
        """
        if (self.show is True) and (episode_id % self.show_every == 0) and (self.environment_type != "godot"):
            self.environment.render()
    
    def assess_mc_success(self, new_state_data):
        """ if the environment is mountaincar, assess whether the agent succeeded
        """
        success = False
        reward_data = 0.0
        if self.environment_name == "MountainCar-v0":
            if new_state_data[0] >= self.environment.goal_position:
                success = True
                reward_data = 1

        return reward_data, success 

    def average_rewards(self, rewards):
        avg_rewards = []
        # transform the rewards to their avergage on the last n episodes 
        # (n being specified in the class parameters)
        for i in range(len(rewards)):  # iterate through rewards
            curr_reward = rewards[i]
            last_n_rewards = [rewards[j] for j in range(i - 100 - 1, i) if j >= 0]
            last_n_rewards.append(curr_reward)
            avg_reward = np.average(last_n_rewards)
            avg_rewards += [avg_reward]

        return avg_rewards

if __name__ == "__main__":
    # set the working dir to the script's directory
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    data = get_params("actor_critic_params")
    session_parameters = data["session_info"]
    session_parameters["agent_info"] = data["agent_info"]

    sess = Session(session_parameters)
    sess.run()
