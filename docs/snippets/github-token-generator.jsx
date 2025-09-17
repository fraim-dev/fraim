import { useState } from 'react'

export const GitHubTokenGenerator = () => {
  const [repoUrl, setRepoUrl] = useState('')
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

  const createTokenOnGitHub = () => {
    setError('')
    
    const parsed = parseRepoUrl()
    if (!parsed) return

    // Generate the Personal Access Token creation URL
    const baseUrl = 'https://github.com/settings/personal-access-tokens/new'
    const params = new URLSearchParams({
      name: 'Fraim Risk Flagger Token',
      description: 'Token for Fraim Risk Flagger to create status checks and request reviews',
      target_name: parsed.owner,
      expires_in: 'none', // Does not expire
      contents: 'read',
      metadata: 'read',
      members: 'read',
      pull_requests: 'write',
      statuses: 'write'
    })
    
    const generatedUrl = `${baseUrl}?${params.toString()}`
    
    // Open the GitHub token creation page
    window.open(generatedUrl, '_blank', 'noopener,noreferrer')
  }

  const createRepositorySecret = () => {
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
        Create Personal Access Token
      </h4>

      <div className="mb-6 text-sm text-zinc-600 dark:text-zinc-400">
        <p className="mb-4"><strong>Note:</strong> This token will be configured with the following permissions:</p>
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

        <div className="flex flex-col gap-3 mt-6">
          <button
            onClick={createTokenOnGitHub}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            1. Create Token on GitHub
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>
          
          <div className="text-sm text-zinc-600 dark:text-zinc-400 py-3">
            <p>After creating your token in step 1, copy the generated Personal Access Token and use it to create a GitHub Action secret named <code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">GH_TOKEN</code> in step 2.</p>
          </div>
          
          <button
            onClick={createRepositorySecret}
            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            2. Add PAT to Github Action Secrets
            <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
