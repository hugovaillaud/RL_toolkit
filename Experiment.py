from Session import *
import matplotlib.pyplot as plt

class Experiment:
    def __init__(self, params={}):
        self.num_sessions = None
        self.sessions = []
        self.environment_name = None
        self.varying_params = []
        self.avg_results = None
        self.avg_length = None

        self.set_params_from_dict(params)

    def set_params_from_dict(self, params={}):
        self.num_sessions = params.get("num_sessions", 0)
        self.avg_results = params.get("avg_results", False)
        self.avg_length = params.get("avg_length", 100)

        self.init_sessions(params)

    def init_sessions(self, params):
        """ Initialize sessions with parameters """
        # isolate the parameters
        session_params = params.get("session_info")
        agent_params = session_params.get("agent_info")
        function_approximator_params = agent_params.get("function_approximator_info")

        # creating the sessions with their own values
        for n_session in range(self.num_sessions):
            for key in params["session_variants"].keys():
                if params["session_variants"][key]["level"] == "agent":
                    agent_params[key] = params["session_variants"][key]["values"][n_session]
                elif params["session_variants"][key]["level"] == "function_approximator":
                    function_approximator_params[key] = params["session_variants"][key]["values"][n_session]
                agent_params["function_approximator_info"] = function_approximator_params
                session_params["agent_info"] = agent_params
            self.sessions.append(Session(session_params))

        for key in params["session_variants"].keys():
            self.varying_params.append((key, params["session_variants"][key]["level"]))


    def run(self):
        rewards_by_session = []
        for session in self.sessions:
            rewards = session.run()
            rewards_by_session.append(rewards)

        rewards_by_session = self.modify_rewards(rewards_by_session)
        self.plot_rewards(rewards_by_session)

    def modify_rewards(self, rewards_by_session):
        rewards_to_return = rewards_by_session
        # transform the rewards to their avergage on the last n episodes (n being specified in the class parameters)
        if self.avg_results is True:
            avg_rewards_by_session = []

            for rewards in rewards_by_session:  # split the rewards sequences by episode
                avg_rewards = []
                for i in range(len(rewards)):  # we iterate through rewards
                    curr_reward = rewards[i]
                    last_n_rewards = [rewards[j] for j in range(i - self.avg_length - 1, i) if j >= 0]
                    last_n_rewards.append(curr_reward)
                    avg_reward = np.average(last_n_rewards)
                    avg_rewards += [avg_reward]
                avg_rewards_by_session.append(avg_rewards)
            rewards_to_return = avg_rewards_by_session

        return rewards_to_return

    def plot_rewards(self, rewards_by_session):

        plt.plot(np.array(rewards_by_session).T)
        plt.xlabel("Episode")
        plt.ylabel("reward Per Episode")
        plt.yscale("linear")
        plt.legend(
            [[f'{varying_param[0]}: {getattr(session.agent,varying_param[0])}' if varying_param[1] == "agent" else f'{varying_param[0]}: {getattr(session.agent.function_approximator,varying_param[0])}' for varying_param in self.varying_params] for
             session in self.sessions])
        plt.show()



if __name__ == "__main__":
    experiment_parameters = {"num_sessions": 2,
                             "session_variants": {
                                 "trace_decay": {"values": [0.4, 0.9],
                                                   "level": "agent"},
                                 "control_method": {"values": ["sarsa", "sarsa"],
                                                 "level": "agent"}
                             },
                             "avg_results": True
                             }

    session_parameters = {"num_episodes": 500,
                          "environment_name": "MountainCar-v0",
                          "return_results": True}

    agent_parameters = {"num_actions": 3,
                        "is_greedy": True,
                        "epsilon": 0.95,
                        "control_method": "sarsa",
                        "function_approximation_method": "tile coder",
                        "discount_factor": 1,
                        "learning_rate": 0.1,
                        "function_approximator_info": {
                            "num_tiles": 4,
                            "num_tilings": 32,
                            "type": "tile coder"
                        }}
    """
    agent_parameters = {"num_actions": 3,
                        "is_greedy": False,
                        "epsilon": 0.9,
                        }
    function_approx_parameters = {"type": "tile",
                                  "state_dim": 4,
                                  "action_dim": 2,
                                  "memory_size": 1000,
                                  "update_target_rate": 100,
                                  "batch_size": 128,
                                  "learning_rate": 0.01,
                                  "discount_factor": 0.90
                                  }

    agent_parameters["function_approximator_info"] = function_approx_parameters
    """
    session_parameters["agent_info"] = agent_parameters
    experiment_parameters["session_info"] = session_parameters

    experiment = Experiment(experiment_parameters)
    experiment.run()

