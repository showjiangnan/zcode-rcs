export interface RcsGrant { workspacePath: string; workspaceIdentity?: string; remoteSessionId?: string }
export interface RcsWorkspace { handle:string; name:string; workspacePath:string; workspaceIdentity?:string|null; remoteSessionId?:string|null }
export interface RcsHost { id:string; generation:string; name:string; workspaces:RcsWorkspace[] }
export interface RcsDevice { id:string; name:string; incarnation:string; online:boolean }
export interface RcsClient { id:string; name:string; expiresAt:number; createdAt:number }
export interface RcsCapabilities { bridgeVersion:1; rpcCodec:1; agentWire:3; services:Record<string,{methods:readonly string[];events:readonly string[]}>; workspace:RcsGrant; nativeDesktop:false }
export interface RcsAttachment { id:string; deviceId:string; hostId:string; hostGeneration:string; workspaceHandle:string; capabilities:RcsCapabilities; state:'ready'|'connected' }
export interface RcsHttpOptions { endpoint:string; request?:typeof fetch; cookieAuthentication?:boolean; now?:()=>number; timeoutMs?:number; signal?:AbortSignal }
export declare class RcsHttpClient {
 constructor(options:RcsHttpOptions); readonly endpoint:string;
 login(key:string,name?:string):Promise<void>; restore():Promise<void>; checkCompatibility():Promise<void>; refreshIfNeeded():Promise<void>; logout():Promise<void>;
 call<T>(path:string,method?:string,body?:unknown):Promise<T>;
 listDevices():Promise<RcsDevice[]>; listHosts(deviceId:string):Promise<RcsHost[]>;
 attach(input:{deviceId:string;hostId:string;hostGeneration:string;workspaceHandle:string}):Promise<RcsAttachment>;
 detach(id:string):Promise<void>; socketTicket(id:string):Promise<{ticket:string}>;
 listClients():Promise<RcsClient[]>; revokeClient(id:string):Promise<void>;
 resourceUrl(attachmentId:string,path:string):string; readResource(attachmentId:string,path:string,range?:string):Promise<Response>;
}
export interface RcsSocket { readyState:number; bufferedAmount:number; binaryType:string; send(value:string|Uint8Array<ArrayBuffer>):void; close(code?:number,reason?:string):void; addEventListener(type:string,callback:(event:{data?:unknown;code?:number;reason?:string})=>void):void; removeEventListener(type:string,callback:(event:{data?:unknown;code?:number;reason?:string})=>void):void }
export type RcsSocketFactory=(url:string)=>RcsSocket;
export type RcsPublicRequest={ service: "file"; method: "searchWorkspaceFiles" | "readdir" | "stat" | "checkFilesExist" | "resolvePath" | "readTextFile" | "readMediaPreview" | "readFileRange" | "readBinaryPreview" | "listWorkspaceFilesLength" | "listWorkspaceFilesRange" | "readWorkspaceFileSearchIgnore" | "applyWorkspaceFileSearchIgnoreTransform" | "writeWorkspaceFileSearchIgnore" | "writeTextFile"; args?: unknown[] }
 | { service: "git"; method: "getRepositorySummary" | "getWorkspaceRepositoryInfo" | "getLocalBranches" | "getCommitGraph" | "switchBranch" | "createBranchAndSwitch" | "getChanges" | "getIgnoredPaths" | "getDiff" | "getBranchComparison" | "stagePaths" | "unstagePaths" | "discardPaths" | "generateCommitMessage" | "commit" | "push" | "getIdentity" | "refresh"; args?: unknown[] }
 | { service: "git-checkpoint"; method: "createCheckpoint" | "diffCheckpoints" | "restoreBetweenCheckpoints" | "deleteCheckpoint"; args?: unknown[] }
 | { service: "system"; method: "info" | "listIntegratedTerminalShells"; args?: unknown[] }
 | { service: "terminal"; method: "create" | "write" | "resize" | "dispose" | "list" | "attach" | "detach"; args?: unknown[] }
 | { service: "setting"; method: "get" | "update"; args?: unknown[] }
 | { service: "zcode-task"; method: "initialize" | "createTask" | "sendPrompt" | "deliverSessionMessage" | "sendSessionMessageDeliveryResult" | "enqueueTaskCommand" | "promoteTaskCommand" | "cancelTaskCommand" | "stopGeneration" | "compactSession" | "goalSession" | "respondPermission" | "respondElicitation" | "closeTask" | "resumeTask" | "listTasks" | "listPinnedTaskIds" | "listPinnedTasks" | "listDeletedTaskIds" | "listTaskList" | "createTaskGroup" | "renameTaskGroup" | "updateTaskGroupColor" | "deleteTaskGroup" | "listGroupedTaskViewStructure" | "applyGroupedTaskViewOrder" | "listArchivedTasks" | "archiveStaleTasks" | "archiveWorkspaceTasks" | "getTaskSnapshot" | "getTaskSnapshotWithEtag" | "getTaskSnapshotBody" | "getTaskSnapshotRef" | "getTaskSnapshotToolCallsSlice" | "getTaskMeta" | "getTaskConfigOptions" | "getTaskModelSelection" | "setAssistantMessageFeedback" | "setMode" | "setConfigOption" | "setModel" | "setAutomationSessionConfig" | "getModelTrajectory" | "getTaskTokenUsage" | "deleteTask" | "deleteArchivedTask" | "deleteArchivedTasks" | "renameTask" | "setTaskPinned" | "setTaskUnread" | "archiveTask" | "unarchiveTask" | "branchTaskFromPrompt"; args?: unknown[] }
 | { service: "window-controller"; method: "deleteArchivedTask" | "deleteArchivedTasks" | "listTaskList" | "mutateTask" | "subscribeControllerV4" | "resyncControllerV4" | "unsubscribeControllerV4"; args?: unknown[] }
 | { service: "zcode-agent"; method: "prepareStorage" | "getStorageStartupState" | "initialize" | "getWorkspaceRuntimeIdentity" | "createSession" | "resumeSession" | "listSessions" | "listSessionSubagents" | "getTaskTokenUsage" | "readSession" | "readSessionMessages" | "readSessionDebug" | "readSessionEvents" | "readWorkspacePresentation" | "grantWorkspaceHookTrust" | "listMcpServerStatuses" | "listPlugins" | "getPluginReferenceCatalog" | "getSkillReferenceCatalog" | "listSavedWorkflows" | "getSavedWorkflow" | "updateSavedWorkflowMeta" | "deleteSavedWorkflow" | "listSavedWorkflowRuns" | "moveSavedWorkflow" | "resolveSuggestedPluginReference" | "getPluginsOverview" | "addPluginMarketplace" | "removePluginMarketplace" | "updatePluginMarketplace" | "installPlugin" | "cancelPluginOperation" | "uninstallPlugin" | "updatePlugin" | "restoreBuiltinPlugin" | "configurePlugin" | "resetPluginConfig" | "validatePlugin" | "describePlugin" | "setPluginEnabled" | "listAutomations" | "createAutomation" | "updateAutomation" | "deleteAutomation" | "setAutomationEnabled" | "restartAutomation" | "runAutomationNow" | "listAutomationRuns" | "deleteAutomationRun" | "generateWorkspaceText" | "testModelConnectivity" | "sendPrompt" | "compactSession" | "reviewProjectMemory" | "workspaceMemory" | "readProjectMemoryReview" | "cancelProjectMemoryReview" | "goalSession" | "closeSession" | "setModel" | "setThoughtLevel" | "setMode" | "respondSessionRuntimePreferences" | "helloConversationV4" | "initializeConversationV4" | "subscribeConversationV4" | "resyncConversationV4" | "unsubscribeConversationV4" | "conversationRowsRangeV4" | "conversationPlansV4" | "conversationWorkflowRunEventsV4" | "conversationWorkflowRunsV4" | "conversationWorkflowRunArtifactsV4" | "conversationWorkflowRunArtifactDataV4" | "conversationWorkflowRunArtifactReadV4" | "conversationWorkflowRunWorkspaceV4" | "conversationWorkflowRunNodeResultV4" | "backgroundBashOutputV4" | "conversationFileChangesV4" | "conversationFileRewindPreviewV4" | "sendConversationCommandV4" | "queryConversationCommandsV4" | "attachmentBeginV4" | "attachmentChunkV4" | "attachmentCommitV4" | "attachmentAbortV4" | "attachmentPreviewSourceV4" | "attachmentReadV4" | "conversationAttachmentReadV4" | "conversationAttachmentStatV4" | "subscribeSessionsIndexV4" | "resyncSessionsIndexV4" | "unsubscribeSessionsIndexV4" | "subscribeWorkspaceConfigV4" | "resyncWorkspaceConfigV4" | "unsubscribeWorkspaceConfigV4"; args?: unknown[] }
 | { service: "zcode-session"; method: "initializeWorkspace" | "getWorkspaceRuntimeIdentity" | "readWorkspacePresentation" | "createSession" | "resumeSession" | "listSessions" | "readSession" | "readSessionMessages" | "readSessionEvents" | "promoteDeferredDraftSession" | "closeSession" | "closeDeferredDraftSession" | "setModel" | "setThoughtLevel" | "setMode"; args?: unknown[] }
 | { service: "model-selection"; method: "getView"; args?: unknown[] }
 | { service: "provider-settings"; method: "getView" | "refresh" | "createPersonalProvider" | "savePersonalProviderOverlay" | "deletePersonalProvider" | "reorderPersonalProviders" | "reorderPersonalModels" | "addPersonalModel" | "renamePersonalModel" | "deletePersonalModel" | "savePersonalModelDraft" | "setPersonalModelEnabled" | "discoverModels" | "setPersonalModelFastMode" | "testModelConnectivity"; args?: unknown[] }
 | { service: "image-generation"; method: "getSettings" | "saveSettings" | "listModels" | "validate"; args?: unknown[] }
 | { service: "skills"; method: "list" | "setEnabled" | "buildPromptContext" | "copyToCommon" | "removeFromCommon" | "deleteSkill"; args?: unknown[] }
 | { service: "plugins"; method: "getOverview" | "addMarketplace" | "removeMarketplace" | "updateMarketplace" | "installPlugin" | "uninstallPlugin" | "setPluginEnabled"; args?: unknown[] }
 | { service: "plugin-management"; method: "listPlugins" | "getPluginReferenceCatalog" | "resolveSuggestedPluginReference" | "getPluginsOverview" | "addPluginMarketplace" | "removePluginMarketplace" | "updatePluginMarketplace" | "installPlugin" | "cancelPluginOperation" | "uninstallPlugin" | "updatePlugin" | "restoreBuiltinPlugin" | "configurePlugin" | "resetPluginConfig" | "validatePlugin" | "describePlugin" | "setPluginEnabled"; args?: unknown[] }
 | { service: "subagents"; method: "list" | "setEnabled" | "setBuiltInModelOverride" | "setPluginAgentModelOverride" | "createAgent" | "updateAgent" | "deleteAgent"; args?: unknown[] }
 | { service: "commands"; method: "list" | "writeCommandFile" | "updateCommandFile" | "deleteCommandFile" | "setCommandEnabled"; args?: unknown[] }
 | { service: "hooks"; method: "loadHooks" | "saveHooks" | "grantWorkspaceHookTrust"; args?: unknown[] }
 | { service: "memory"; method: "listProjectMemories" | "readProjectMemoryFile"; args?: unknown[] }
 | { service: "usage-stats"; method: "getAppUsageSnapshot" | "getCodingPlanUsageSnapshot" | "getCodingPlanResetStatus" | "requestCodingPlanResetOpportunity" | "useCodingPlanReset" | "markCodingPlanResetHistoryRead" | "getSnapshot" | "getEntitlementSnapshot"; args?: unknown[] }
 | { service: "coding-plan-subscription"; method: "getDynamicWorkflowClientConfig"; args?: unknown[] }
 | { service: "client-scenes"; method: "list"; args?: unknown[] }
 | { service: "file-watcher"; method: "watch" | "unwatch"; args?: unknown[] }
 | { service: "media-preview"; method: "prepare" | "refreshPlaybackUrl" | "release"; args?: unknown[] }
 | { service: "broadcast"; method: "send" | "sendWithAcknowledgements"; args?: unknown[] };
export type RcsPublicSubscription={ service: "terminal"; event: "onDynamicData" | "onDynamicExit" | "onDynamicReplayData"; arg?: unknown }
 | { service: "zcode-task"; event: "onDynamicStreamEvent" | "onDynamicTaskTerminalOutcome" | "onDynamicTaskReady" | "onDynamicTaskEvent" | "onDynamicWorkspaceEvent"; arg?: unknown }
 | { service: "window-controller"; event: "onDynamicControllerFrame"; arg?: unknown }
 | { service: "zcode-agent"; event: "onDynamicStorageStartupState" | "onDynamicPluginOperationProgress" | "onDynamicSessionEvent" | "onDynamicConversationFrame" | "onDynamicSessionsIndexFrame" | "onDynamicWorkspaceConfigFrame" | "onAgentRuntimeRestarted" | "onAgentRuntimeLifecycle"; arg?: unknown }
 | { service: "model-selection"; event: "onDidChange"; arg?: unknown }
 | { service: "provider-settings"; event: "onDidChange"; arg?: unknown }
 | { service: "plugin-management"; event: "onDynamicPluginOperationProgress"; arg?: unknown }
 | { service: "file-watcher"; event: "onDynamicChange"; arg?: unknown }
 | { service: "broadcast"; event: "onMessage"; arg?: unknown };
export declare class RcsRpcConnection {
 constructor(attachment:RcsAttachment,socket:RcsSocket,http?:RcsHttpClient);
 readonly attachment:RcsAttachment; readonly ready:Promise<void>;
 readonly closed:(listener:(event:{code:number;reason:string})=>void)=>{dispose():void};
 static connect(http:RcsHttpClient,attachment:RcsAttachment,socketFactory?:RcsSocketFactory):Promise<RcsRpcConnection>;
 call<T=unknown>(request:RcsPublicRequest):Promise<T>;
 subscribe<T=unknown>(request:RcsPublicSubscription,listener:(event:T)=>void):{dispose():void};
 dispose(closeSocket?:boolean,outcome?:{code:number;reason:string}):void;
}
export declare const RCS_SERVICE_MANIFEST:Record<string,{methods:readonly string[];events:readonly string[]}>;
export declare const RCS_BRIDGE_VERSION:1, RCS_RPC_CODEC_VERSION:1, RCS_AGENT_WIRE_VERSION:3;
export declare function encodeRcsFrame(id:string,payload:Uint8Array):Uint8Array;
export declare function decodeRcsFrame(bytes:Uint8Array):{attachmentId:string;payload:Uint8Array};
