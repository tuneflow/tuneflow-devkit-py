# tuneflow-devkit-py
Python DevKit for TuneFlow

## Architecture

![Architecture](./public/images/sdk_illustration.jpg)

## Roadmap

1. Implement basic python socket.io server that receives and prints messages from plugin-dev-plugin.
2. Define a `Plugin` class that follows the same interface as [base_plugin.ts](https://github.com/andantei/tuneflow/blob/master/src/base_plugin.ts).
3. Define a hello world plugin that defines the basic plugin info (providerId, providerDisplayName, etc...)
4. Handles `set-song` message and returns the plugin info, PluginDevPlugin should be able to show the debugging plugin's info.
5. Add `init` and `run` interface into `Plugin` class.
6. Write a plugin that splits a track into two voices, similar to [tuneflow-helloworld-plugin](https://github.com/andantei/tuneflow-helloworld-plugin/blob/main/index.ts)
7. Handles `init-plugin` and `run-plugin` in the devkit, and call the plugin's `init` and `run` methods and returns the corresponding results, in PluginDevPlugin we should be able to run the debugging plugin and split the selected track into two voices.

## References

* [tuneflow](https://github.com/andantei/tuneflow)
* [tuneflow-devkit](https://github.com/andantei/tuneflow-devkit)
* [tuneflow-helloworld-plugin](https://github.com/andantei/tuneflow-helloworld-plugin)
* [tuneflow-proto](https://github.com/andantei/tuneflow-proto)
* [插件系统是如何运作的？](https://help.tuneflow.com/zh/developer/how-we-run-plugins.html)