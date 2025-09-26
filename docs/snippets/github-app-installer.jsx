import { useState } from 'react'

export const GitHubAppInstaller = () => {
  const [repoUrl, setRepoUrl] = useState('')
  const [isOrganization, setIsOrganization] = useState(true)
  const [error, setError] = useState('')

  const parseRepoUrl = () => {
    if (!repoUrl.trim()) {
      setError('Please enter a repository URL')
      return null
    }

    try {
      // Parse the GitHub repository URL to extract owner/org and repo
      const url = new URL(repoUrl.trim())
      
      if (url.hostname !== 'github.com') {
        setError('Please enter a valid GitHub repository URL')
        return null
      }

      // Extract the path and get the owner and repo
      const pathParts = url.pathname.split('/').filter(part => part.length > 0)
      
      if (pathParts.length < 2) {
        setError('Invalid repository URL format. Expected: https://github.com/owner/repo')
        return null
      }

      return {
        owner: pathParts[0],
        repo: pathParts[1]
      }
    } catch (err) {
      setError('Invalid URL format. Please enter a valid GitHub repository URL.')
      return null
    }
  }

  const createGitHubApp = () => {
    setError('')
    
    const parsed = parseRepoUrl()
    if (!parsed) return

    // Generate the GitHub App creation URL
    const baseUrl = isOrganization 
      ? `https://github.com/organizations/${parsed.owner}/settings/apps/new`
      : `https://github.com/settings/apps/new`
    
    const params = new URLSearchParams({
      name: `Fraim Risk Flagger - ${parsed.owner}`,
      description: 'GitHub App for Fraim Risk Flagger to create status checks and request reviews',
      url: 'https://www.fraim.dev',
      contents: 'read',
      metadata: 'read',
      members: 'read',
      pull_requests: 'write',
      statuses: 'write',
      webhook_active: 'false'
    })
    
    const generatedUrl = `${baseUrl}?${params.toString()}`
    
    // Open the GitHub App creation page
    window.open(generatedUrl, '_blank', 'noopener,noreferrer')
  }

  const generatePrivateKey = () => {
    setError('')
    
    const parsed = parseRepoUrl()
    if (!parsed) return

    // Generate the private key URL
    const appName = `fraim-risk-flagger-${parsed.owner.toLowerCase()}`
    const privateKeyUrl = isOrganization
      ? `https://github.com/organizations/${parsed.owner}/settings/apps/${appName}#private-key`
      : `https://github.com/settings/apps/${appName}#private-key`
    
    // Open the private key generation page
    window.open(privateKeyUrl, '_blank', 'noopener,noreferrer')
  }

  const installApp = () => {
    setError('')
    
    const parsed = parseRepoUrl()
    if (!parsed) return

    // Generate the app installation URL
    const appName = `fraim-risk-flagger-${parsed.owner.toLowerCase()}`
    const installUrl = `https://github.com/apps/${appName}/installations/new`
    
    // Open the app installation page
    window.open(installUrl, '_blank', 'noopener,noreferrer')
  }

  const openAppSettings = () => {
    setError('')
    
    const parsed = parseRepoUrl()
    if (!parsed) return

    // Generate the app settings URL to find the App ID
    const appName = `fraim-risk-flagger-${parsed.owner.toLowerCase()}`
    const settingsUrl = isOrganization
      ? `https://github.com/organizations/${parsed.owner}/settings/apps/${appName}`
      : `https://github.com/settings/apps/${appName}`
    
    // Open the app settings page
    window.open(settingsUrl, '_blank', 'noopener,noreferrer')
  }

  const createRepositorySecrets = () => {
    setError('')
    
    const parsed = parseRepoUrl()
    if (!parsed) return

    // Generate the repository secrets URL
    const secretsUrl = `https://github.com/${parsed.owner}/${parsed.repo}/settings/secrets/actions/new`
    
    // Open the GitHub repository secrets page
    window.open(secretsUrl, '_blank', 'noopener,noreferrer')
  }

  return (
    <div className="p-6 border dark:border-zinc-700 rounded-lg not-prose bg-zinc-50 dark:bg-zinc-900">
      <h4 className="text-lg font-semibold mb-4 text-zinc-900 dark:text-zinc-100">
        Install Fraim Risk Flagger GitHub App
      </h4>

      <div className="mb-6 text-sm text-zinc-600 dark:text-zinc-400">
        <p className="mb-4"><strong>Note:</strong> This GitHub App will be configured with the following permissions:</p>
        <ul className="list-disc list-inside space-y-2 ml-4">
          <li><code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">contents:read</code> - Read repository contents</li>
          <li><code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">metadata:read</code> - Read repository metadata</li>
          <li><code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">members:read</code> - Read organization member information</li>
          <li><code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">pull_requests:write</code> - Create and update pull request reviews</li>
          <li><code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">statuses:write</code> - Create status checks</li>
        </ul>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">
            Repository URL
          </label>
          <input
            type="url"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/your-org/your-repo"
            className="w-full px-3 py-2 border border-zinc-300 dark:border-zinc-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 dark:bg-zinc-800 dark:text-zinc-100"
          />
          {error && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="isOrganization"
            checked={isOrganization}
            onChange={(e) => setIsOrganization(e.target.checked)}
            className="h-4 w-4 text-green-600 focus:ring-green-500 border-zinc-300 rounded"
          />
          <label htmlFor="isOrganization" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Organization account (uncheck for personal account)
          </label>
        </div>

        <div className="flex flex-col gap-3 mt-6">
          <button
            onClick={createGitHubApp}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            1. Create GitHub App
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>
          
          <div className="text-sm text-zinc-600 dark:text-zinc-400 py-2">
            <p>After creating your GitHub App in step 1, you'll need to generate a private key for authentication.</p>
          </div>
          
          <button
            onClick={generatePrivateKey}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            2. Generate Private Key
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>

          <div className="text-sm text-zinc-600 dark:text-zinc-400 py-2">
            <p>Next, install the GitHub App on your repository or organization.</p>
          </div>

          <button
            onClick={installApp}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            3. Install GitHub App
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>

          <div className="text-sm text-zinc-600 dark:text-zinc-400 py-2">
            <p>Now you need to get your App ID and set up GitHub Action secrets. First, get your App ID:</p>
          </div>

          <button
            onClick={openAppSettings}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            4. Get App ID
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>

          <div className="text-sm text-zinc-600 dark:text-zinc-400 py-2">
            <div className="bg-zinc-100 dark:bg-zinc-800 p-3 rounded-md">
              <p className="font-medium mb-2">Before proceeding to step 5:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Copy your App ID from the page that opens in step 4</li>
                <li>Copy your private key to clipboard using: <code className="bg-zinc-200 dark:bg-zinc-700 px-1 rounded">cat ~/Downloads/fraim-risk-flagger-*.*.private-key.pem | pbcopy</code></li>
              </ol>
            </div>
          </div>

          <button
            onClick={createRepositorySecrets}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            5. Add GitHub Action Secrets
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>

          <div className="text-sm text-zinc-600 dark:text-zinc-400 py-2">
            <div className="bg-zinc-100 dark:bg-zinc-800 p-3 rounded-md">
              <p className="font-medium mb-2">Create these two secrets:</p>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li><code className="bg-zinc-200 dark:bg-zinc-700 px-1 rounded">GH_APP_ID</code> - Your App ID from step 4</li>
                <li><code className="bg-zinc-200 dark:bg-zinc-700 px-1 rounded">GH_APP_PRIVATE_KEY</code> - Your private key (paste from clipboard)</li>
              </ul>
              <p className="mt-2 text-xs">Now you can use these in your GitHub Action with <code className="bg-zinc-200 dark:bg-zinc-700 px-1 rounded">github-app-id</code> and <code className="bg-zinc-200 dark:bg-zinc-700 px-1 rounded">github-app-private-key</code> parameters.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
