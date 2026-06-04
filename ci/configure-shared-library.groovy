// Phase 6 · M3 — 전역 공유 라이브러리 'url-shortener-shared' 를 코드로 등록한다.
// 적용: Manage Jenkins → Script Console 에 붙여넣기, 또는
//       curl --data-urlencode "script=$(cat ci/configure-shared-library.groovy)" <JENKINS>/scriptText
import jenkins.model.Jenkins
import jenkins.plugins.git.GitSCMSource
import jenkins.plugins.git.traits.BranchDiscoveryTrait
import org.jenkinsci.plugins.workflow.libs.GlobalLibraries
import org.jenkinsci.plugins.workflow.libs.LibraryConfiguration
import org.jenkinsci.plugins.workflow.libs.SCMSourceRetriever

def source = new GitSCMSource('https://github.com/soyeon911/TestAutomation.git')
source.setId('url-shortener-shared-src')
source.setCredentialsId('')                       // 공개 저장소 → 자격 증명 불필요
source.setTraits([new BranchDiscoveryTrait()])

def retriever = new SCMSourceRetriever(source)
retriever.setLibraryPath('jenkins/shared-library')  // 라이브러리 루트는 서브디렉터리

def lib = new LibraryConfiguration('url-shortener-shared', retriever)
lib.setDefaultVersion('main')
lib.setImplicit(false)
lib.setAllowVersionOverride(true)

def gl = Jenkins.get().getDescriptorByType(GlobalLibraries.class)
gl.setLibraries([lib])
gl.save()

println 'configured libraries: ' + gl.getLibraries().collect {
    it.name + ' (defaultVersion=' + it.defaultVersion + ', path=' + it.retriever.libraryPath + ')'
}
